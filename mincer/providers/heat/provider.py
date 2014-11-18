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
import string
import tempfile
import time
import uuid

from concurrent import futures
from Crypto.PublicKey import RSA
import glanceclient
import heatclient.client as heatclient
from heatclient.common import template_utils
import heatclient.exc as heatclientexc
import keystoneclient.exceptions as keystoneexc
import keystoneclient.v2_0 as keystone_client
import novaclient.client as novaclient
import six
import swiftclient

import mincer.exceptions
import mincer.utils.ssh

LOG = logging.getLogger(__name__)

RETRY_MAX = 1000


class Heat(object):

    """The Heat provide which run stacks on an OpenStack."""

    def __init__(self, params={}, args={}):
        """constructor of the Heat provider

        :param params: the configuration structure
        :type params: dict
        :param args: the CLI arguments as parsed by argparse
        :type args: argparse.Namespace
        :returns: None
        :rtype: None

        """
        self.params = params
        self.args = args
        self._keystone = None
        self._novaclient = None
        self.medias = {}
        self.key_pairs = {}
        self.floating_ips = {}
        self._application_stack = None
        self._tester_stack = None
        self.priv_key, self.pub_key = self._generate_key_pairs()
        self._check_sessions = []
        self.ssh_client = mincer.utils.ssh.SSH(self.priv_key)

        tmp = str(uuid.uuid4())

        self.name = "mincer-%s" % tmp[:8]

        # TODO(Gonéri): to move in a static resource file
        self._gateway_heat_template = """description: Zoubida
heat_template_version: '2013-05-23'
outputs:
  tester_instance_public_ip:
    description: Floating IP address of tester_instance
    value:
      get_attr: [tester_instance_floating_ip, floating_ip_address]
parameters:
  app_key_name: {description: Name of a key pair, type: string}
  private_network: {description: UUID of the internal network, type: string}
  public_network: {description: UUID of the public network, type: string}
  volume_id_base_image: {description: The VM root system, type: string}
resources:
  server_security_group:
    properties:
      description: Add security group rules for server
      name: security-group
      rules:
      - {port_range_max: '22',
         port_range_min: '22',
         protocol: tcp, remote_ip_prefix: 0.0.0.0/0}
      - {protocol: icmp, remote_ip_prefix: 0.0.0.0/0}
    type: OS::Neutron::SecurityGroup
  tester_instance:
    metadata:
      os-collect-config: {polling_interval: 1}
    properties:
      flavor: m1.small
      image: {get_param: volume_id_base_image}
      key_name: {get_param: app_key_name}
      networks:
      - port: {get_resource: tester_instance_port}
# TODO(Goneri): user_data_format=SOFTWARE_CONFIG is broken
# with eNoCloud-CA
#      user_data_format: SOFTWARE_CONFIG
    type: OS::Nova::Server
  tester_instance_floating_ip:
    properties:
      floating_network_id: {get_param: public_network}
      port_id: {get_resource: tester_instance_port}
    type: OS::Neutron::FloatingIP
  tester_instance_port:
    properties:
      network_id: {get_param: private_network}
      security_groups:
      - {get_resource: server_security_group}
    type: OS::Neutron::Port
"""

    def _generate_key_pairs(self):
        """Generate ssh key pairs in OpenSSH format.

        :returns: a tuple of string for the key pairs in
        the format (private_key, public_key)
        :rtype: tuple

        """
        private_key = RSA.generate(2048)
        public_key = private_key.publickey()

        # Heat replaces carriage return by spaces then it's escaped
        r_private_key = private_key.exportKey()
        r_public_key = public_key.exportKey("OpenSSH")

        return r_private_key, r_public_key

    def connect(self, identity):
        """Connect Openstack clients.

        :param identity: the OS identity of the environment
        :type identity: dict
        """
        LOG.info("Connecting to %s" % identity['os_auth_url'])
        try:
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
        except (keystoneexc.AuthorizationFailure,
                keystoneexc.Unauthorized) as e:
            LOG.exception(e)
            raise mincer.exceptions.AuthorizationFailure()

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
        """Return a tuple of two dicts.

        The first dict corresponds to the medias which need to be uploaded
        and the second corresponds to the medias which does not.

        :param medias: list of Media objects
        :type medias: list
        :param refresh_medias: list of medias names to refresh
        :type refresh_medias: list
        """
        medias_to_upload = medias.copy()
        for media_to_upload in medias_to_upload.values():
            for media_in_glance in self._glance.images.list():
                if media_in_glance.disk_format != media_to_upload.disk_format:
                    continue
                if media_in_glance.status != 'active':
                    continue
                if media_to_upload.name in refresh_medias:
                    continue
                if 'name' in media_to_upload.filter_on:
                    if media_to_upload.name != media_in_glance.name:
                        continue
                if 'size' in media_to_upload.filter_on:
                    if media_to_upload.size != media_in_glance.size:
                        continue
                if 'checksum' in media_to_upload.filter_on:
                    if media_to_upload.checksum != media_in_glance.checksum:
                        continue
                LOG.info("An image '%s' already exist in Glance (%s) "
                         "and match the criteria (%s)." % (
                             media_to_upload.name,
                             media_in_glance.id,
                             ", ".join(media_to_upload.filter_on)))
                media_to_upload.glance_id = media_in_glance.id

        return medias_to_upload

    def upload(self, medias, refresh_medias):
        """Upload medias in Glance.

        :param medias: list of Media objects
        :type medias: list
        :param refresh_medias: list of medias names to refresh
        :type refresh_medias: list
        """
        medias_to_upload = self._filter_medias(medias, refresh_medias)
        self._upload_medias(medias_to_upload)
        return self._wait_for_medias_in_glance(medias_to_upload)

    def _show_media_upload_status(self, name, fd, size):
        time.sleep(5)
        try:
            LOG.info("%s: %5dM /%5dM" % (
                name,
                fd.tell() / 1024 / 1024,
                size / 1024 / 1024))
        except Exception as e:
            LOG.exception(e)
            pass

    def _upload_medias(self, medias_to_upload):
        for media in medias_to_upload.values():
            if media.glance_id:
                LOG.info("%s already in Glance (%s)" % (
                    media.name, media.glance_id))
                continue

            media.generate()
            image = self._glance.images.create(name=media.name)
            media.glance_id = image.id
            # TODO(Gonéri) clean the image in case of failure
            if media.copy_from:
                LOG.info("Downloading '%s' from %s" % (media.name,
                                                      media.copy_from))
                image.update(container_format='bare',
                             disk_format=media.disk_format,
                             copy_from=media.copy_from)
            else:
                with open(media.getPath(), "rb") as media_fd:
                    LOG.info("Uploading %s to %s" % (media.getPath(),
                                                     media.name))
                    with futures.ThreadPoolExecutor(max_workers=1) as executor:
                        upload = executor.submit(
                            image.update, container_format='bare',
                            disk_format=media.disk_format,
                            data=media_fd)
                        while upload.running():
                            self._show_media_upload_status(
                                media.name,
                                media_fd,
                                media.size)

    def _wait_for_medias_in_glance(self, medias_to_upload):
        parameters = {}
        LOG.info("Checking the image(s) status")
        while len(parameters) != len(medias_to_upload):
            for media in medias_to_upload.values():
                image = self._glance.images.get(media.glance_id)
                LOG.debug("status: %s - %s", image.name, image.status)
                if image.status == 'active':
                    LOG.info("Image %s is ready" % image.name)
                    parameters['volume_id_%s' % image.name] = media.glance_id
                elif image.status == 'killed':
                    raise ImageException("Error while waiting for image")
                else:
                    LOG.info("waiting for %s", media.name)
                    time.sleep(5)
        return parameters

    def register_pub_key(self, test_public_key):
        """Register the public key in the provider

        Create a temporary OpenStack keypair and push the test_public_key. This
        key should be deployed on the node of the application.

        :param test_public_key: the public key
        :type test_public_key: str
        """
        parameters = {}
        try:
            self._novaclient.keypairs.create(self.name, test_public_key)
        except novaclient.exceptions.Conflict:
            LOG.debug("Key %s already created", self.name)
        parameters['app_key_name'] = self.name

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

    def run(self, cmd_tpl, host=None):
        """Call a command on a host

        You can use this method to call a command on a remote host. $foo
        pattern will be replaced by the IP address of the host.

        e.g:
            ping -c 1 $jenkins_instance

        :param cmd_tpl: the command template
        :type cmd_tpl: str
        :param host: the name of the target host
        :type host: str
        :return: a tuple with the returned code and the output
        """
        cmd = self._expand_template(cmd_tpl)

        machines = self.get_machines()
        host_ip = None
        if host:
            try:
                host_ip = machines[host]['primary_ip_address']
            except KeyError:
                LOG.error("'%s' not found in machine list" %
                          host)
                raise ActionFailure()

        session = self.ssh_client.get_transport(host_ip).open_session()

        session.set_combine_stderr(True)
        session.get_pty()
        session.setblocking(0)

        session.exec_command(cmd)

        output = ''
        while not session.exit_status_ready():
            if session.recv_ready():
                data = session.recv(1024)
                output += data

                if session.recv_stderr_ready():
                    LOG.info(session.recv_stderr(1024))
        retcode = session.recv_exit_status()

        LOG.info((
            "command {cmd} output: {output}"
        ).format(
            cmd=cmd,
            output=output
        ))
        session.close()
        if retcode != 0:
            LOG.error((
                "Command {cmd} "
                "returned an unexpected code {retcode}"
            ).format(
                cmd=cmd,
                retcode=retcode
            ))
            raise ActionFailure()
        return (retcode, output)

    def register_check(self, cmd_tpl, interval=5):
        """Register a background check in the provider."""
        cmd = self._expand_template(cmd_tpl)

        session = self.ssh_client.get_transport().open_session()
        session.set_combine_stderr(True)
        session.get_pty()
        session.setblocking(0)

        session.exec_command(
            "bash -c 'set -eu ; while true; do %s;" % (cmd) +
            "sleep %d; done'" % (interval))
        self._check_sessions.append({
            'session': session,
            'cmd': cmd
        })

    def watch_running_checks(self):
        """Watch the status of the running background checks."""
        for check_session in self._check_sessions:
            if 'session' not in check_session:
                continue

            LOG.info(
                "Checking status of background "
                "command '%s' " % check_session['cmd'])
            if check_session['session'].recv_ready():
                LOG.debug(check_session['session'].recv(1024))

            if check_session['session'].recv_stderr_ready():
                LOG.debug(check_session['session'].recv_stderr(1024))

            if check_session['session'].exit_status_ready():
                LOG.error((
                    "command ({cmd}) "
                    "died with return code {retcode}"
                ).format(
                    cmd=check_session['cmd'],
                    retcode=check_session['session'].recv_exit_status()))
                raise ActionFailure()
            else:
                LOG.info("Command is still running")

    def launch_application(self, template_path=None):
        """Start the application infrastructure

        Start the application and gateway stacks and initialize the SSH
        transport.
        """
        if not template_path:
            template_path = self.args.marmite_directory + "/heat.yaml"
        t0 = time.time()
        # Create the gateway stack
        with tempfile.NamedTemporaryFile() as stack_file:
            stack_file.write(bytearray(self._gateway_heat_template, 'UTF-8'))
            stack_file.seek(0)

            tester_id = self.create_or_update_stack(
                name=self.name + "_gway",
                template_path=stack_file.name)

        # Create the app
        application_id = self.create_or_update_stack(
            name=self.name + "_app",
            template_path=template_path)
        success_status = ['COMPLETE', 'CREATE_COMPLETE']
        stack = self.wait_for_status_changes(tester_id, success_status)
        logs = {}
        for output in stack.outputs:
            logs[output['output_key']] = six.StringIO(output['output_value'])
        self._tester_stack = Stack(tester_id, logs)

        logs = {}
        stack = self.wait_for_status_changes(application_id, success_status)
        info = ('stack creation processed in %.2f, final status: %s' %
                (time.time() - t0, stack.status))
        LOG.info(info)
        logs = {'general': six.StringIO(info)}
        for output in stack.outputs:
            logs[output['output_key']] = six.StringIO(output['output_value'])
        self._application_stack = Stack(application_id, logs)

    def init_ssh_transport(self):
        """Initialize the SSH transport through the gateway stack."""
        t = self._tester_stack.get_logs()
        gateway_ip = t['tester_instance_public_ip'].getvalue()

        self.ssh_client.start_transport(gateway_ip)
        session = self.ssh_client.get_transport().open_session()
        session.exec_command('uname -a')

        for host in self.get_machines():
            self.run('uname -a', host=host)

    def get_stack_parameters(self, tpl_files, template, *args):
        """Prepare the parameters, as expected by the stack

        :param tpl_files: the files as returned by
         template_utils.get_template_contents
        :type tpl_files: dict
        :param template: the template as returned by
         template_utils.get_template_contents
        :type template: string
        :param args: the parameters
        :type args: list
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

    def _show_stack_progress(self, stack_id):
            events = self._heat.events.list(stack_id)
            created = set([item.resource_name for item in events if
                           item.resource_status == 'CREATE_COMPLETE'])
            creating = set([item.resource_name for item in events if
                            item.resource_status == 'CREATE_IN_PROGRESS'])
            LOG.info("%i: creating %s" %
                     (len(created),
                      ", ".join(creating - created)))

    # TODO(Gonéri): Should be in the Stack class
    def wait_for_status_changes(self, stack_id, expected_status):
        """Wait untill a stack has a new status.

        :param stack_id: The ID of the stack
        :type stack_id: int
        :param expected_status: the exepected final status
        :type expected_status: a array of strings

        """
        for _ in six.moves.range(1, RETRY_MAX):
            stack = self._heat.stacks.get(stack_id)
            if stack.status in expected_status:
                break
            elif stack.status == 'FAILED':
                LOG.error("Error while creating Stack: %s",
                          stack.stack_status_reason)
                raise StackCreationFailure()
            self._show_stack_progress(stack_id)
            time.sleep(2)
        else:
            raise StackTimeoutException("status: %s" % stack.status)
        return stack

    def create_or_update_stack(self,
                               name=None,
                               stack_id=None,
                               template_path=None,
                               parameters={}):
        """Run the stack and provides the parameters to Heat.

        :param name: name of the stack
        :type name: str
        :param template_path: path of the heat template
        :type template_path: str
        :param params: parameters of the template
        :type params: dict
        :returns: the stack ID
        :rtype: int
        """
        try:
            parameters.update(self.args.extra_params)
        except TypeError:
            pass
        parameters.update(self.key_pairs)
        parameters.update(self.floating_ips)
        parameters['flavor'] = 'm1.small'

        for network in self._novaclient.networks.list():
            parameters['%s_network' % network.label] = network.id

        LOG.info(
            "The following keys are available from your "
            "heat template: " + ", ".join(parameters.keys()))

        # TODO(Gonéri): name param is not used anymore
        tpl_files, template = template_utils.get_template_contents(
            template_path
        )
        stack_params = self.get_stack_parameters(
            tpl_files,
            template,
            self.args.extra_params,
            parameters,
            self.medias)

        if stack_id:
            action_function = self._heat.stacks.update
        else:
            action_function = self._heat.stacks.create

        try:
            resp = action_function(
                stack_id=stack_id,
                stack_name=name,
                parameters=stack_params,
                template=template,
                files=dict(list(tpl_files.items())))
        except heatclientexc.HTTPConflict:
            LOG.error("Stack '%s' failed because of a conflict", name)
            raise AlreadyExisting()
        return stack_id if stack_id else resp['stack']['id']

    # TODO(Gonéri): Should be in the Stack class
    def delete_stack(self, stack_id):
        """Delete a stack

        :param stack_id: the ID of the stack to destroy
        :type stack_id: str

        """
        # TODO(Gonéri) wait for the stack for being deleted
        self._heat.stacks.delete(stack_id)

    def cleanup(self):
        """Clean up the tenant."""
        if self._tester_stack:
            self.delete_stack(self._tester_stack.get_id())
        if self._application_stack:
            self.delete_stack(self._application_stack.get_id())
        if self._novaclient:
            self._novaclient.keypairs.delete(self.name)

    def get_machines(self):
        """Collect machine informations from a running stack.

        :returns: a list of dictionnary describing the machines from
         the running stack
        :rtype: dict
        """
        machines = {}
        for resource in self._heat.resources.list(
                self._application_stack.get_id()):
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
            machines[resource.resource_name] = {
                'name': server.name,
                'resource_name': resource.resource_name,
                'id': resource.physical_resource_id,
                'primary_ip_address': primary_ip_address
            }
        return machines

    def _expand_template(self, cmd_tpl):
        machines = self.get_machines()
        try:
            cmd = string.Template(cmd_tpl).substitute(
                dict((k, v['primary_ip_address'])
                     for k, v in six.iteritems(machines))
            )
        except KeyError as e:
            LOG.error("Hostname %s from the following template '%s' was not "
                      "found in the stack resources." % (e, cmd_tpl))
            raise mincer.exceptions.InstanceNameFromTemplateNotFoundInStack()
        return cmd


class Stack(object):

    """A abstraction layer on top of the stack."""

    def __init__(self, stack_id, logs):
        """Stack object constructor."""
        self.id = stack_id
        self.logs = logs

    def get_id(self):
        """Return the stack id."""
        return self.id

    def get_logs(self):
        """Return the stack log."""
        return self.logs


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


class ActionFailure(Exception):

    """Raised when an action has failed."""
