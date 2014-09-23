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

import tempfile
import unittest

import fixtures
import mock
import novaclient.client as novaclient
import six
import testtools

import mincer.providers.heat. provider as provider

provider.LOG = mock.Mock()


fake_identity = {
    'os_auth_url': 'http://example.com',
    'os_username': 'admin',
    'os_password': 'password',
    'os_tenant_name': 'demo'
}


class fake_args(object):

    def __init__(self):
        self.extra_params = {'roberto': 'sanchez'}
        self.marmite_directory = tempfile.mkdtemp()
        with open(self.marmite_directory + "/heat.yaml", 'w') as f:
            f.write("""
heat_template_version: 2013-05-23

description: >
  Yet another useless Heat template.
""")


class fake_service_catalog(object):

    def url_for(self, service_type='fake_service', endpoint_type='roberto'):

        return "http://somewhere/%s" % service_type


class fake_keystone(object):

    def __init__(self, **kwargs):

        self.service_catalog = fake_service_catalog()
        self.auth_token = "garantie_100%_truly_random"


class fake_novaclient(object):

    class fake_floating_ips(object):
        def __init__(self, **kwargs):
            self._floating_ip_1 = mock.Mock()
            self._floating_ip_1.ip = "127.0.0.1"
            self._floating_ip_1.instance_id = None
            self._floating_ip_2 = mock.Mock()
            self._floating_ip_2.ip = "127.0.0.2"
            self._floating_ip_2.instance_id = None

        def list(self):
            return [self._floating_ip_1, self._floating_ip_2]

        def create(self):
            floating_ip = mock.Mock()
            floating_ip.ip = "127.0.0.3"
            floating_ip.instance_id = None
            return floating_ip

    class fake_servers(object):
        def __init__(self, **kwargs):
            return

        def get(self, server_id):

            iface = mock.Mock()
            iface.fixed_ips = [{'ip_address': '127.0.0.1'}]
            server = mock.Mock()
            server.name = 'robert-%s' % server_id
            server.interface_list.return_value = [iface]
            return server

    class fake_networks(object):
        def __init__(self):
            self._network_1 = mock.Mock()
            self._network_1.id = "1"
            self._network_1.label = "public"
            self._network_2 = mock.Mock()
            self._network_2.id = "2"
            self._network_2.label = "internal"

        def list(self):
            return [self._network_1, self._network_2]

    def __init__(self, **kwargs):
        self.floating_ips = self.fake_floating_ips()
        self.servers = self.fake_servers()
        self.networks = self.fake_networks()
        self.keypairs = mock.Mock()


class fake_heatclient(object):
    class fake_resources(object):
        def __init__(self, **kwargs):
            return

        def list(self, stack_id):
            mock1 = mock.Mock()
            mock1.resource_type = 'OS::Nothing::Here'
            mock2 = mock.Mock()
            mock2.resource_type = 'OS::Nova::Server'
            mock2.resource_name = 'nerf'
            mock2.physical_resource_id = 'lapin'
            return [mock1, mock2]

    class fake_stacks(object):
        def __init__(self, **kwargs):
            return

        def create(self, **kwargs):
            return {"stack": {"id": "12345"}}

        def get(self, stack_id):
            mockStack = mock.Mock()
            mockStack.outputs = [{
                'description': "foobar",
                'output_key': "stdout",
                'output_value': "my output"}]
            mockStack.status = 'CREATE_COMPLETE'
            return mockStack

        def validate(self, template='a', files='b'):
            return({'Parameters':
                    {'flavor':
                     {'Default': 'toto'},
                     'roberto': {}}})

    class fake_events(object):
        def __init__(self, *args, **kwargs):
            return

        def list(self, *args, **kwargs):
            return []

    def __init__(self, **kwargs):
        self.resources = self.fake_resources()
        self.stacks = self.fake_stacks()
        self.events = self.fake_events()


class fake_glanceclient(object):

    class fake_images(object):
        def __init__(self, create_image_id, **kwargs):
            self.create_image_id = create_image_id
            self.fake_image_1 = mock.Mock()
            self.fake_image_1.name = "name_1"
            self.fake_image_1.id = 0
            self.fake_image_1.status = 'active'
            self.fake_image_2 = mock.Mock()
            self.fake_image_2.name = "name_2"
            self.fake_image_2.id = 1
            self.fake_image_2.status = 'active'
            self.fake_image_3 = mock.Mock()
            self.fake_image_3.name = "name_3"
            self.fake_image_3.id = 2
            self.fake_image_3.status = 'killed'
            self.fake_images = [self.fake_image_1, self.fake_image_2,
                                self.fake_image_3]

        def list(self):
            return self.fake_images

        def create(self, *args, **kwargs):
            return self.fake_images[self.create_image_id]

        def get(self, image_id):
            return self.fake_images[image_id]

    def __init__(self, create_image_id):
        self.images = self.fake_images(create_image_id)


def fake_client_with_create_image_0(*args, **kwargs):
    return fake_glanceclient(0)


def fake_client_with_create_image_1(*args, **kwargs):
    return fake_glanceclient(1)


def fake_client_with_create_image_2(*args, **kwargs):
    return fake_glanceclient(2)


class mock_callable(object):
    def __call__(self, **kwargs):
        class_to_load = kwargs["class"]
        return class_to_load(kwargs["params"])


class fake_swift(object):
    @staticmethod
    def Connection(preauthurl=None, preauthtoken=None):
        class fake_swift_conn(object):
            def put_object(self, container, name, obj):
                pass
        return fake_swift_conn()


class TestProvider(testtools.TestCase):
    def setUp(self):

        super(TestProvider, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('heatclient.v1.client.Client', fake_heatclient)
    def test_create(self):
        fa = fake_args()
        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.connect(fake_identity), None)
        template_path = fa.marmite_directory + "/heat.yaml"
        stack_result = my_provider.create_stack("test_stack",
                                                template_path, {})
        self.assertIsInstance(stack_result, provider.Stack)

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('heatclient.v1.client.Client', fake_heatclient)
    def test_create_with_missing_params(self):
        fa = fake_args()
        args = fake_args()
        args.extra_params = {}
        my_provider = provider.Heat(args=args)
        self.assertEqual(my_provider.connect(fake_identity), None)
        template_path = fa.marmite_directory + "/heat.yaml"
        self.assertRaises(
            provider.InvalidStackParameter,
            my_provider.create_stack,
            "test_stack", template_path, {})

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('heatclient.v1.client.Client', fake_heatclient)
    def test_application(self):
        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.connect(fake_identity), None)
        my_provider._novaclient = fake_novaclient()
        my_provider.name = "test_stack"
        actual = my_provider.launch_application()
        self.assertIsInstance(actual, dict)
        self.assertTrue("stdout" in actual)
        self.assertEqual(actual["stdout"].getvalue(), "my output")

    def test_register_floating_ips(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        test_res = my_provider.register_floating_ips(
            {"test_floating_ip": "127.0.0.1"})
        expected_parameters = {"floating_ip_test_floating_ip": "127.0.0.1"}
        self.assertDictEqual(my_provider.floating_ips, expected_parameters)
        self.assertDictEqual(test_res, {"test_floating_ip": "127.0.0.1"})

    def test_register_floating_ips_unknown_floating_iP(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"pub_1": "1.2.3.4"})

    def test_register_static_floating_ips_already_reserved(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"test_floating_ip": "127.0.0.1",
                           "test_floating_ip2": "127.0.0.1"})

    def test_register_static_floating_ips_already_used(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider._novaclient.floating_ips.list()[0].instance_id = "id"
        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"test_floating_ip": "127.0.0.1"})

    def test_register_dynamic_floating_ips_already_allocated(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        test_res = my_provider.register_floating_ips(
            {"test_floating_ip": "dynamic"})
        expected_parameters_1 = {"floating_ip_test_floating_ip": "127.0.0.1"}
        expected_parameters_2 = {"floating_ip_test_floating_ip": "127.0.0.2"}
        self.assertTrue(my_provider.floating_ips == expected_parameters_1 or
                        my_provider.floating_ips == expected_parameters_2)
        self.assertTrue(test_res == {"test_floating_ip": "127.0.0.1"} or
                        test_res == {"test_floating_ip": "127.0.0.2"})

    def test_register_dynamic_floating_ips_creation(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()

        test_res = my_provider.register_floating_ips(
            {"float_1": "127.0.0.1", "float_2": "127.0.0.2",
             "test_floating_ip": "dynamic"})
        self.assertDictEqual(my_provider.floating_ips,
                             {"floating_ip_float_1": "127.0.0.1",
                              "floating_ip_float_2": "127.0.0.2",
                              "floating_ip_test_floating_ip": "127.0.0.3"})
        self.assertDictEqual(test_res, {"test_floating_ip": "127.0.0.3",
                                        "float_1": "127.0.0.1",
                                        "float_2": "127.0.0.2"})

    def test_get_machines(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider._heat = fake_heatclient()
        my_provider._application_stack = provider.Stack("george", {})
        reference = {
            'nerf': {
                'id': 'lapin',
                'name': 'robert-lapin',
                'primary_ip_address': '127.0.0.1',
                'resource_name': 'nerf'
            }}
        self.assertEqual(reference, my_provider.get_machines())

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('glanceclient.Client', fake_client_with_create_image_0)
    def test_filter_medias(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.connect({
            'os_auth_url': 'http://nowhere',
            'os_username': 'admin',
            'os_password': 'password',
            'os_tenant_name': 'demo'
        })
        medias = {"name_1": "", "name_2": "", "name_3": ""}
        to_up, to_not_up = my_provider._filter_medias(medias, ["name_2"])

        res_to_up = {"name_2": None, "name_3": None}
        res_to_not_up = {"name_1": 0}
        self.assertDictEqual(to_up, res_to_up)
        self.assertDictEqual(to_not_up, res_to_not_up)

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('swiftclient.client', fake_swift)
    def test_put_object(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.connect({
            'os_auth_url': 'http://nowhere',
            'os_username': 'admin',
            'os_password': 'password',
            'os_tenant_name': 'demo'
        })
        my_provider.swift.put_object('log', 'robert', 'gaspart')

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('glanceclient.Client', fake_client_with_create_image_0)
    def test_upload_with_copy_from(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.connect({
            'os_auth_url': 'http://nowhere',
            'os_username': 'admin',
            'os_password': 'password',
            'os_tenant_name': 'demo'
        })
        fm = mock.Mock()
        fm.generate.return_value = None

        medias = {"name_1": fm, "name_2": fm}
        actual_parameters = my_provider.upload(medias, ["name_1"])
        expected_parameters = {'volume_id_name_1': 0, 'volume_id_name_2': 1}
        self.assertDictEqual(actual_parameters, expected_parameters)

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('glanceclient.Client', fake_client_with_create_image_1)
    @mock.patch('%s.open' % six.moves.builtins.__name__)
    def test_upload_with_local_image(self, mock_open):
        my_provider = provider.Heat(args=fake_args())
        my_provider.connect({
            'os_auth_url': 'http://nowhere',
            'os_username': 'admin',
            'os_password': 'password',
            'os_tenant_name': 'demo'
        })

        fake_image = mock.Mock()
        fake_image.name = "name_1"
        fake_image.id = 0
        fake_image.copy_from = False
        fake_image.generate.return_value = None

        medias = {"name_1": "", "name_2": fake_image}
        actual_parameters = my_provider.upload(medias, ["name_2"])
        expected_parameters = {'volume_id_name_1': 0, 'volume_id_name_2': 1}
        self.assertDictEqual(actual_parameters, expected_parameters)

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('glanceclient.Client', fake_client_with_create_image_2)
    def test_upload_exception(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.connect({
            'os_auth_url': 'http://nowhere',
            'os_username': 'admin',
            'os_password': 'password',
            'os_tenant_name': 'demo'
        })
        fm = mock.Mock()
        fm.generate.return_value = None

        medias = {"name_1": fm, "name_2": ""}
        self.assertRaises(provider.ImageException,
                          my_provider.upload, medias, ["name_1"])

    def test_regiter_pub_key_ok(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider.register_pub_key('bob')
        self.assertEqual(
            my_provider.key_pairs,
            {'app_key_name': my_provider.name})

    def test_regiter_pub_key_dup(self):
        def keypairs_create_failure(name, key):
            raise novaclient.exceptions.Conflict("a", "b")

        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider._novaclient.keypairs.create = keypairs_create_failure
        my_provider.register_pub_key('bob')
        self.assertEqual(
            my_provider.key_pairs,
            {'app_key_name': my_provider.name})

    def test_run(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider.get_machines = mock.Mock(return_value={})
        my_provider.ssh_client = mock.Mock()

        self.assertRaises(provider.ActionFailure, my_provider.run, "toto")

    def test_init_ssh_transport(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.run = mock.Mock(return_value=True)
        my_provider.ssh_client = mock.Mock()
        my_provider.get_machines = mock.Mock(return_value={'toto': {}})
        tester_stack = mock.Mock()
        log_public_ip = mock.Mock()
        log_public_ip.getvalue.return_value = '1.2.3.4'
        tester_stack.get_logs.return_value = {
            'tester_instance_public_ip': log_public_ip}
        my_provider._tester_stack = tester_stack
        self.assertEqual(my_provider.init_ssh_transport(), None)
        my_provider.run.assert_called_with('uname -a', host='toto')

    def test_register_check(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider.get_machines = mock.Mock(return_value={})
        my_provider.ssh_client = mock.Mock()
        self.assertEqual(my_provider.register_check("echo roy", 5), None)

    def test_watch_running_checks_no_session(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._check_sessions = [{}]
        self.assertEqual(my_provider.watch_running_checks(), None)

    def test_watch_running_checks_dead_session(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.ssh_client = mock.Mock()
        my_fake_session = mock.Mock()
        my_fake_session.recv_ready.return_value = False
        my_fake_session.recv_stderr_ready.return_value = True
        my_fake_session.recv_stderr.return_value = "ko"
        my_fake_session.exit_status_ready.return_value = True
        my_fake_session.recv_exit_status.return_value = 1
        my_provider._check_sessions = [{'session': my_fake_session,
                                        'cmd': 'cmd'}]
        self.assertRaises(provider.ActionFailure,
                          my_provider.watch_running_checks)
        self.assertTrue(provider.LOG.debug.called)
        self.assertTrue(provider.LOG.error.called)

    def test_watch_running_checks_success_session(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.ssh_client = mock.Mock()
        my_fake_session = mock.Mock()
        my_fake_session.recv_ready.return_value = True
        my_fake_session.recv.return_value = "ok"
        my_fake_session.exit_status_ready.return_value = True
        my_fake_session.recv_exit_status.return_value = 0
        my_provider._check_sessions = [{'session': my_fake_session,
                                        'cmd': 'cmd'}]
        self.assertRaises(provider.ActionFailure,
                          my_provider.watch_running_checks)
        self.assertTrue(provider.LOG.debug.called)

    def test_watch_running_checks_running_session(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider.ssh_client = mock.Mock()
        my_fake_session = mock.Mock()
        my_fake_session.exit_status_ready.return_value = False
        my_provider._check_sessions = [{'session': my_fake_session,
                                        'cmd': 'cmd'}]
        self.assertEqual(my_provider.watch_running_checks(), None)
        self.assertTrue(provider.LOG.info.called)

if __name__ == '__main__':
    unittest.main()
