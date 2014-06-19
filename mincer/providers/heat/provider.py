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

        self.heat_endpoint = self._keystone.service_catalog.url_for(
            service_type='orchestration')

        self._heat = heatclient.Client('1', endpoint=self.heat_endpoint,
                                       token=self._keystone.auth_token,
                                       auth_url=identity['os_auth_url'],
                                       username=identity['os_username'],
                                       password=identity['os_password'],
                                       )

    def _filter_medias(self, glance_client, medias, refresh_medias):
        """Returns a tuple of two dicts.

        The first dict corresponds to the medias which need to be uploaded
        and the second corresponds to the medias which does not.

        :param glance_client: the glance client
        :type medias: glanceclient.Client
        :param medias: list of Media objects
        :type medias: list
        :param refresh_medias: list of medias names to refresh
        :type refresh_medias: list
        """

        # Make an association of names and IDs of existent Glance images.
        names_ids_images = {}
        for image in glance_client.images.list():
            names_ids_images[image.name] = image.id

        medias_to_upload = {}
        medias_to_not_upload = {}

        for media_name in medias.keys():
            if media_name not in refresh_medias:
                if media_name in names_ids_images.keys():
                    medias_to_not_upload[media_name] = \
                        names_ids_images[media_name]
                else:
                    medias_to_upload[media_name] = None
            else:
                medias_to_upload[media_name] = None

        return medias_to_upload, medias_to_not_upload

    def upload(self, medias, refresh_medias):
        """Upload medias in Glance.

        :param medias: list of Media objects
        :type medias: list
        :param refresh_medias: list of medias names to refresh
        :type refresh_medias: list
        """

        parameters = dict()
        glance_endpoint = self._keystone.service_catalog.url_for(
            service_type='image')

        glance = glanceclient.Client(
            1,
            glance_endpoint,
            token=self._keystone.auth_token)

        medias_to_up, medias_to_not_up = self._filter_medias(glance,
                                                          medias,
                                                          refresh_medias)

        # populate parameters for medias to not upload
        for media_name in medias_to_not_up:
            parameters['volume_id_%s' % media_name] = \
                medias_to_not_up[media_name]

        for media_name in medias_to_up:
            LOG.debug("uploading media: '%s'", media_name)
            media = medias[media_name]
            media.generate()

            image = glance.images.create(name=media_name)
            # TODO(Gonéri) clean the image in case of failure
            if media.copy_from:
                image.update(container_format='bare',
                             disk_format=media.disk_format,
                             copy_from=media.copy_from)
            else:
                with open(media.getPath(), "rb") as media_data:
                    image.update(container_format='bare',
                                 disk_format=media.disk_format,
                                 data=media_data)

            while image.status != 'active':
                if image.status == 'killed':
                    raise Exception("Glance error while waiting for image")
                time.sleep(5)
                image = glance.images.get(image.id)
                LOG.info("waiting for %s", media.name)
            parameters['volume_id_%s' % image.name] = image.id
            LOG.debug("status: %s - %s", media.name, image.status)
        return parameters

    def register_key_pairs(self, key_pairs):
        """Register key pairs.
        :param key_pairs: the key pairs
        :type  key_pairs: dict
        """
        parameters = dict()
        for name in key_pairs:
            try:
                self._novaclient.keypairs.create(name, key_pairs[name])
            except novaclient.exceptions.Conflict:
                LOG.debug("Key %s already created", name)
            # TODO(Gonéri), this force the use of a sole key
            parameters['key_name'] = name
        return parameters

    def register_floating_ips(self, floating_ips):
        """Ensure that the provided floating ips are available. Push them
        on the Heat stack parameters.
        """
        parameters = dict()
        for name in floating_ips:
            ip = floating_ips[name]
            found = None
            # TODO(yassine), not correct for two floating ips
            for entry in self._novaclient.floating_ips.list():
                if ip != entry.ip:
                    continue
                parameters['floating_ip_%s' % name] = entry.id
                found = True
            if not found:
                raise UnknownFloatingIP("floating ip '%s' not found" % ip)
        return parameters

    def launch_application(self, name, medias, key_pairs, floating_ips):
        parameters = dict()
        try:
            parameters.update(self.args.extra_params)
        except TypeError:
            pass
        parameters.update(medias)
        parameters.update(key_pairs)
        parameters.update(floating_ips)
        parameters['flavor'] = 'm1.small'
        stack_id = self.create_stack(
                name + str(uuid.uuid4()),
                self.args.marmite_directory + "/heat.yaml",
                parameters)
        self.application_stack_id = stack_id

    def create_stack(self, name, heat_file, params):
        """Run the stack and provides the parameters to Heat."""

        tpl_files, template = template_utils.get_template_contents(
            heat_file
        )

        self._heat.stacks.list()
        try:
            resp = self._heat.stacks.create(
                stack_name=name,
                parameters=params,
                template=template,
                files=dict(list(tpl_files.items())))
        except heatclientexc.HTTPConflict:
            LOG.error("Stack '%s' failed because of a conflict", name)
            raise AlreadyExisting()

        stack_id = resp['stack']['id']
        while True:
            stack = self._heat.stacks.get(stack_id)
            LOG.info("Stack status: %s", stack.status)
            if stack.status == 'FAILED':
                raise StackCreationFailure()
            if stack.status != 'IN_PROGRESS':
                break
            time.sleep(10)
        LOG.info("Stack final status: %s", stack.status)
        for line in self.retrieve_log(stack_id):
            LOG.info(line)
        return stack_id

    def delete_stack(self, stack_id):
        self._heat.stacks.delete(stack_id)

    def retrieve_log(self, stack_id):
        stack = self._heat.stacks.get(stack_id=stack_id)
        lines = []
        for output in stack.outputs:
            lines.append("Call of '%s'" % output['description'])
            for line in output['output_value'].split('\n'):
                lines.append("%s: %s" % (
                    output['output_key'],
                    line))
        return lines

    def cleanup_application(self):
        self.delete_stack(self.application_stack_id)

    def get_machines(self):
        """Return a list of dictionnary describing the machines from
           the running stack
        """
        machines = []
        for resource in self._heat.resources.list(self.application_stack_id):
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


class StackCreationFailure(Exception):
    """Exception raised if the stack failed to start properly."""
