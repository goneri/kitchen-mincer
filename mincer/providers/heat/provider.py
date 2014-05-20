# -*- coding: utf-8 -*-
#
# Copyright 2014 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import time
import uuid

import glanceclient
import heatclient.client as heatclient
from heatclient.common import template_utils
import heatclient.exc as heatclientexc
import keystoneclient.v2_0 as keystone_client
import novaclient.client as novaclient

LOG = logging.getLogger(__name__)


class Heat(object):
    """The Heat provider which run stacks on an OpenStack."""

    def __init__(self, params={}, args={}):
        self.params = params
        self.args = args
        self._keystone = None
        self._parameters = {'flavor': 'm1.small'}

    def connect(self, identity):
        """This method connect to the Openstack.
        :param identity: the OS identity of the environment
        :type identity: dict
        """
        self._keystone = keystone_client.Client(
            auth_url=identity['os_auth_url'],
            username=identity['os_username'],
            password=identity['os_password'],
            tenant_name=identity['os_tenant_name'])
        self._novaclient = novaclient.Client(2,
                                        identity['os_username'],
                                        identity['os_password'],
                                        auth_url=identity['os_auth_url'],
                                        project_id=identity['os_tenant_name'])

    def upload(self, medias):
        """Upload medias in Glance.

        :param medias: list of Media objects
        :type medias: list
        """

        glance_endpoint = self._keystone.service_catalog.url_for(
            service_type='image')

        glance = glanceclient.Client(
            1,
            glance_endpoint,
            token=self._keystone.auth_token)

        # Make an association of checksum and id of existent Glance images.
        checksum_ids_images = {}
        for image in glance.images.list():
            try:
                checksum_ids_images[image.checksum] = image.id
            except AttributeError:
                LOG.warn("checksum for image '%s' not found", image.id)

        # Upload each media if necessary
        for media in medias:
            LOG.debug("uploading media: '%s', checksum: '%s'",
                      media.name, media.checksum)

            if media.checksum in checksum_ids_images.keys():
                self._parameters['volume_id_%s' % media.name] = \
                    checksum_ids_images[media.checksum]
                continue
            image = glance.images.create(name=media.name)
            # TODO(Gonéri) clean the image in case of failure
            if media.getPath():
                with open(media.getPath(), "rb") as media_data:
                    image.update(container_format='bare',
                                 disk_format=media.disk_format,
                                 data=media_data)
            elif media.copy_from:
                image.update(container_format='bare',
                             disk_format=media.disk_format,
                             copy_from=media.copy_from)
            while image.status != 'active':
                if image.status == 'killed':
                    raise Exception("Glance error while waiting for image")
                time.sleep(5)
                image = glance.images.get(image.id)
                LOG.info("waiting for %s", media.name)
            self._parameters['volume_id_%s' % image.name] = image.id
            LOG.debug("status: %s - %s", media.name, image.status)

    def register_key_pairs(self, key_pairs):
        """Register key pairs.
        :param key_pairs: the key pairs
        :type  key_pairs: dict
        """
        for name in key_pairs:
            try:
                self._novaclient.keypairs.create(name, key_pairs[name])
            except novaclient.exceptions.Conflict:
                LOG.debug("Key %s already created", name)
            # TODO(Gonéri), this force the use of a sole key
            self._parameters['key_name'] = name

    def register_floating_ips(self, floating_ips):
        """Ensure that the provided floating ips are available. Push them
        on the Heat stack parameters.
        """
        for name in floating_ips:
            ip = floating_ips[name]
            found = None
            # TODO(yassine), not correct for two floating ips
            for entry in self._novaclient.floating_ips.list():
                if ip != entry.ip:
                    continue
                self._parameters['floating_ip_%s' % name] = entry.id
                found = True
            if not found:
                raise UnknownFloatingIP("floating ip '%s' not found" % ip)

    def create(self, name):
        """Run the stack and provides the parameters to Heat. """
        heat_endpoint = self._keystone.service_catalog.url_for(
            service_type='orchestration')

        tpl_files, template = template_utils.get_template_contents(
            self.args.marmite_directory + "/heat.yaml"
        )

        self.heat = heatclient.Client('1', endpoint=heat_endpoint,
                                      token=self._keystone.auth_token)

        stack_name = "%s--%s" % (name, str(uuid.uuid4()))
        try:
            resp = self.heat.stacks.create(
                stack_name=stack_name,
                parameters=self._parameters,
                template=template,
                files=dict(list(tpl_files.items())),
                timeout_mins=60)
        except heatclientexc.HTTPConflict:
            LOG.error("Stack '%s' failed because of a conflict", stack_name)
            raise AlreadyExisting()

        self._stack_id = resp['stack']['id']
        while True:
            stack = self.heat.stacks.get(self._stack_id)
            LOG.info("Stack status: %s", stack.status)
            if stack.status != 'IN_PROGRESS':
                break
            time.sleep(10)
        LOG.info("Stack final status: %s", stack.status)

    def delete(self):
        self.heat.stacks.delete(self._stack_id)

    def get_machines(self):
        """Return a list of dictionnary describing the machines from
           the running stack
        """
        machines = []
        for resource in self.heat.resources.list(self._stack_id):
            if resource.resource_type != "OS::Nova::Server":
                continue
            server = self._novaclient.servers.get(
                resource.physical_resource_id)
            ifaces = server.interface_list()
            primary_ip_address = None
            iface = ifaces.pop()
            if iface and \
                len(iface.fixed_ips) > 0 and \
                'ip_address' in iface.fixed_ips[0]:
                primary_ip_address = iface.fixed_ips[0]['ip_address']
            machines.append({
                'name': server.name,
                'resource_name': resource.resource_name,
                'id': resource.physical_resource_id,
                'primary_ip_address': primary_ip_address
            })
        return machines


class AlreadyExisting(Exception):
    """Exception raised when there is a conflict with a stack
    already deployed.
    """


class UnknownFloatingIP(Exception):
    """Exception raised when the floating IP is unknown."""


class UploadError(Exception):
    """Exception raised when the mincer failed to upload a media."""
