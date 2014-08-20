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
import six
import swiftclient

LOG = logging.getLogger(__name__)

RETRY_MAX = 1000


class Heat(object):
    """The Heat provider which run stacks on an OpenStack."""

    def __init__(self, params={}, args={}):
        self.params = params
        self.args = args
        self._keystone = None
        self.medias = {}
        self.key_pairs = {}
        self.floating_ips = {}

    def connect(self, identity):
        """This method creates Openstack clients and connects to APIs.

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
        self.glance_endpoint = self._keystone.service_catalog.url_for(
            service_type='image')
        self.swift_endpoint = self._keystone.service_catalog.url_for(
            service_type='object-store',
            endpoint_type='publicURL')

        self._heat = heatclient.Client('1', endpoint=self.heat_endpoint,
                                       token=self._keystone.auth_token,
                                       auth_url=identity['os_auth_url'],
                                       username=identity['os_username'],
                                       password=identity['os_password'],
                                       )
        self._glance = glanceclient.Client(
            1,
            self.glance_endpoint,
            token=self._keystone.auth_token)

        self.swift = swiftclient.client.Connection(
            preauthurl=self.swift_endpoint,
            preauthtoken=self._keystone.auth_token,
        )

    def _filter_medias(self, medias, refresh_medias):
        """Returns a tuple of two dicts.

        The first dict corresponds to the medias which need to be uploaded
        and the second corresponds to the medias which does not.

        :param medias: list of Media objects
        :type medias: list
        :param refresh_medias: list of medias names to refresh
        :type refresh_medias: list
        """

        # Make an association of names and IDs of existent Glance images.
        names_ids_images = {}
        for image in self._glance.images.list():
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

        parameters = {}

        medias_to_up, medias_to_not_up = self._filter_medias(medias,
                                                             refresh_medias)

        # populate parameters for medias to not upload
        for media_name in medias_to_not_up:
            LOG.debug("not upload 'volume_id_%s'" % media_name)
            parameters['volume_id_%s' % media_name] = \
                medias_to_not_up[media_name]

        for media_name in medias_to_up:
            LOG.debug("upload '%s'", media_name)
            media = medias[media_name]
            media.generate()

            image = self._glance.images.create(name=media_name)
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
                    raise ImageException("Error while waiting for image")
                time.sleep(5)
                image = self._glance.images.get(image.id)
                LOG.info("waiting for %s", media.name)
            parameters['volume_id_%s' % image.name] = image.id
            LOG.debug("status: %s - %s", image.name, image.status)
        return parameters

    def register_key_pairs(self, marmite_key_pair, test_public_key):
        """Register the key pair.

        :param marmite_key_pair: the key pair
        :type  marmite_key_pair: dict
        :param test_public_key: the public key pair for test purpose
        :type  test_key_pair: str
        """
        parameters = {'test_public_key': test_public_key}
        for name in marmite_key_pair:
            try:
                self._novaclient.keypairs.create(name, marmite_key_pair[name])
            except novaclient.exceptions.Conflict:
                LOG.debug("Key %s already created", name)
            parameters['app_key_name'] = name

        self.key_pairs = parameters

    def _reserve_static_floating_ips(self, static_floating_ips,
                                     remote_floating_ips):
        """Reserve static floating IPs.

        This function ensure that the static floating IPs are available in the
        floating IP pool of the environment and returns the corresponding
        template parameters.

        :param static_floating_ips: the static floating IPs retrieved from
        the marmite
        :type static_floating_ips: dict
        :param remote_floating_ips: the floating IPs retrieved from the
        environment
        :type remote_floating_ips: dict
        :return: the reserved floating IPs
        """
        output_floating_ips = {}
        # first, we reserved the statics floating IPs
        # once reserved they must be in output_floating_ips
        for name in static_floating_ips:
            static_ip = static_floating_ips[name]

            if static_ip not in remote_floating_ips:
                raise FloatingIPError("floating ip '%s' not allocated"
                                      % static_ip)
            if remote_floating_ips[static_ip].instance_id is not None:
                instance_use_fip = remote_floating_ips[static_ip].instance_id
                raise FloatingIPError("'%s' already used by instance '%s'"
                                      % (static_ip, instance_use_fip))
            if static_ip in output_floating_ips.values():
                # retrieve the floating IP name of the one which
                # is already reserved
                already_reserved = [k for k, v in
                                    six.iteritems(output_floating_ips)
                                    if v == static_ip][0]
                raise FloatingIPError("'%s' already reserved for '%s'" %
                                      (static_ip, already_reserved))

            # here we can safely reserve the floating IP and provide it
            # to the Heat template parameters
            self.floating_ips['floating_ip_%s' % name] = str(static_ip)
            output_floating_ips[name] = str(static_ip)

        return output_floating_ips

    def _reserve_dynamic_floating_ips(self, already_reserved_ip,
                                      dynamic_floating_ips,
                                      remote_floating_ips):
        """Reserve dynamic floating IPs.

        This function tries to reuse free floating IPs from the pool of the
        environment if there is no available floating IPs it will allocate
        a new one. Finally, it returns the corresponding template parameters.

        :param already_reserved_ip: the already reserved floating IPs
        :type already_reserved_ip: dict
        :param dynamic_floating_ips: the dynamic floating IPs retrieved from
        the marmite
        :type dynamic_floating_ips: dict
        :param remote_floating_ips: the floating IPs retrieved from the
        environment
        :type remote_floating_ips: dict
        :return: the reserved floating ips
        :param dynamic_floating_ips:
        :param remote_floating_ips:
        :return: the reserved floating IPs
        """
        output_floating_ips = dict(already_reserved_ip)
        # in a first time we check if we can reuse a free floating IP already
        # allocated in the environment, if not we create a new one.
        for name in dynamic_floating_ips:
            for r_fip in remote_floating_ips:
                # If the already allocated floating IP is not reserved
                if r_fip not in output_floating_ips.values():
                    # Use it instead of allocating a new one
                    self.floating_ips['floating_ip_%s' % name] = str(r_fip)
                    output_floating_ips[name] = str(r_fip)
                    break
            # If there is no free floating IP in the environment
            if not output_floating_ips.get(name):
                # Then create a new one
                new_fip = self._novaclient.floating_ips.create()
                self.floating_ips['floating_ip_%s' % name] = str(new_fip.ip)
                output_floating_ips[name] = str(new_fip.ip)

        return output_floating_ips

    def register_floating_ips(self, marmite_floating_ips):
        """Prepare the floating IPs in the tenant

        Ensure that the static floating ips are available and creates the
        dynamic ones. Push them on the Heat stack parameters.

        :param marmite_floating_ips: the floating specified in the marmite
        :type marmite_floating_ips: dict
        :return: all used floating ips
        :type: dict
        """
        remote_floating_ips = {}
        for entry in self._novaclient.floating_ips.list():
            remote_floating_ips[entry.ip] = entry

        # reserve static floating IPs
        static_floating_ips = dict((k, v) for k, v in
                                   six.iteritems(marmite_floating_ips)
                                   if v != 'dynamic')
        static_reserved_floating_ips = self._reserve_static_floating_ips(
            static_floating_ips, remote_floating_ips)

        # reserve dynamic floating IPs
        dynamic_floating_ips = dict((k, v) for k, v in
                                    six.iteritems(marmite_floating_ips)
                                    if v == 'dynamic')
        dynamic_reserved_floating_ips = self._reserve_dynamic_floating_ips(
            static_reserved_floating_ips, dynamic_floating_ips,
            remote_floating_ips)

        return dict(static_reserved_floating_ips,
                    **dynamic_reserved_floating_ips)

    def launch_application(self):
        parameters = {}
        try:
            parameters.update(self.args.extra_params)
        except TypeError:
            pass
        parameters.update(self.key_pairs)
        parameters.update(self.floating_ips)
        parameters['flavor'] = 'm1.small'
        stack_result = self.create_stack(
                self.name + str(uuid.uuid4()),
                self.args.marmite_directory + "/heat.yaml",
                parameters)
        self.application_stack_id = stack_result["stack_id"]
        return stack_result["logs"]

    def get_stack_parameters(self, tpl_files, template, *args):
        """Prepare the parameters, as expected by the stack

           :param tpl_files: as returned by
           template_utils.get_template_contents
           :param template: as returned by
            template_utils.get_template_contents
           :param *args: the parameters
           :type *args: list
           :return: a dictionary
           :rtype: dict
        """
        validate_ret = self._heat.stacks.validate(
            template=template,
            files=dict(list(tpl_files.items())))

        if validate_ret is None:
            LOG.info("Failed to validate the heat.yaml file")
            raise StackCreationFailure()

        stack_params = {}
        for name in validate_ret['Parameters']:
            try:
                default = validate_ret['Parameters'][name]['Default']
                stack_params[name] = default
            except KeyError:
                pass

            for arg in args:
                if arg is None:
                    continue
                if name not in arg:
                    continue
                stack_params[name] = arg[name]

        missing = set(
            validate_ret['Parameters'].keys()) - set(
                stack_params.keys())
        if missing:
            LOG.error("Parameters '%s' are expected by the stack "
                      "but is not provided" % (', '.join(missing)))
            raise InvalidStackParameter()

        return stack_params

    def create_stack(self, name, template_path, params):
        """Run the stack and provides the parameters to Heat.

        :param name: name of the stack
        :type name: str
        :param template_path: path of the heat template
        :type template_path: str
        :param params: parameters of the template
        :type params: dict
        :returns: a dictionary with a key "stack_id" and a key "logs"
        :rtype: dict
        """

        tpl_files, template = template_utils.get_template_contents(
            template_path
        )
        stack_params = self.get_stack_parameters(
            tpl_files,
            template,
            self.args.extra_params,
            params,
            self.medias)

        try:
            resp = self._heat.stacks.create(
                stack_name=name,
                parameters=stack_params,
                template=template,
                files=dict(list(tpl_files.items())))
        except heatclientexc.HTTPConflict:
            LOG.error("Stack '%s' failed because of a conflict", name)
            raise AlreadyExisting()

        oldevents = []
        stack_id = resp['stack']['id']
        for _ in six.moves.range(1, RETRY_MAX):
            stack = self._heat.stacks.get(stack_id)
            newevents = self._heat.events.list(stack_id)
            diffevents = list(set(newevents) - set(oldevents))
            for i in diffevents:
                LOG.info("%s - %s", i.resource_name, i.event_time)
            if stack.status in ('COMPLETE', 'CREATE_COMPLETE'):
                break
            elif stack.status == 'FAILED':
                LOG.error("Error while creating Stack: %s",
                          stack.stack_status_reason)
                raise StackCreationFailure()
            time.sleep(10)
        else:
            raise StackTimeoutException("status: %s" % stack.status)

        LOG.info("Stack final status: %s", stack.status)

        logs = {}
        for output in stack.outputs:
            logs[output['output_key']] = six.StringIO(output['output_value'])
        return {"stack_id": stack_id, "logs": logs}

    def delete_stack(self, stack_id):
        self._heat.stacks.delete(stack_id)

    def cleanup_application(self):
        self.delete_stack(self.application_stack_id)

    def get_machines(self):
        """Collect machine informations from a running stack.

        :returns: a list of dictionnary describing the machines from
        the running stack
        :rtype: dict
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
    """Exception raised when there is a conflict with a stack."""


class FloatingIPError(Exception):
    """Exception raised when an error occurs for a given floating IP."""


class UploadError(Exception):
    """Exception raised when the mincer failed to upload a media."""


class StackCreationFailure(Exception):
    """Exception raised if the stack failed to start properly."""


class StackTimeoutException(Exception):
    """Exception raised if the stack is not created in time."""


class InvalidStackParameter(Exception):
    """The parameters do not match what the stack expect."""


class ImageException(IndexError):
    """Raised when an error occurs while uploading an image."""
