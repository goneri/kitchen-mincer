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

import fixtures
import keystoneclient.exceptions as keystoneexc
import mock
import novaclient.client as novaclient
import six
import testtools

import mincer.exceptions
import mincer.providers.heat. provider as provider

provider.LOG = mock.Mock()


fake_identity = {
    'os_auth_url': 'http://example.domain',
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


class TestProvider(testtools.TestCase):

    def setUp(self):
        super(TestProvider, self).setUp()
        self.useFixture(fixtures.NestedTempfile())
        self.provider = provider.Heat(args=fake_args())

    @mock.patch('keystoneclient.v2_0.Client', mock.Mock())
    @mock.patch('novaclient.client.Client', mock.Mock())
    @mock.patch('glanceclient.Client', mock.Mock())
    @mock.patch('heatclient.common.template_utils.get_template_contents',
                mock.Mock(return_value=({'a': 'b'}, '/somewhere.yaml')))
    @mock.patch('heatclient.v1.client.Client')
    def test_create(self, heatclient):
        self.provider._heat = mock.Mock()
        self.provider._heat.stacks.create.return_value = {'stack': {'id': 1}}
        self.provider._novaclient = mock.Mock()
        self.provider._novaclient.networks.list.return_value = []
        self.provider.pub_key = "this is a pub key"
        self.provider.get_stack_parameters = mock.Mock()
        self.provider.register_pub_key = mock.Mock()
        template_path = "/heat.yaml"
        mystack = mock.Mock()
        mystack.status = 'CREATE_COMPLETE'
        mystack.outputs = [{'output_key': 'foo', 'output_value': 'bar'}]
        self.provider.wait_for_status_changes = \
            mock.Mock(return_value=mystack)
        stack_id = self.provider.create_or_update_stack(
            name="test_stack",
            template_path=template_path,
            parameters={})
        self.assertEqual(1, stack_id)
        self.provider.get_stack_parameters.assert_called_with(
            {'a': 'b'},
            '/somewhere.yaml',
            {'roberto': 'sanchez'},
            {'flavor': 'm1.small', 'roberto': 'sanchez'},
            {})

    @mock.patch('heatclient.common.template_utils.get_template_contents',
                mock.Mock(return_value=({'a': 'b'}, '/somewhere.yaml')))
    def test_create_with_missing_params(self):
        args = fake_args()
        args.extra_params = {}
        my_provider = provider.Heat(args=args)
        my_provider._heat = mock.Mock()
        my_provider._heat.stacks.validate.return_value = {
            'Parameters': {'george': {'Default': 'a'}, 'helmout': {}}}
        my_provider._novaclient = mock.Mock()
        my_provider._novaclient.networks.list.return_value = []
        template_path = args.marmite_directory + "/heat.yaml"
        self.assertRaises(
            provider.InvalidStackParameter,
            my_provider.create_or_update_stack,
            "test_stack", template_path, {})

    def test_application(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        my_provider._heat = mock.Mock()
        my_provider._heat.stacks.create.return_value = {'stack': {'id': 1}}
        mock_network = mock.Mock()
        mock_network.label = "Mocked network"
        mock_network.id = 1
        my_provider._novaclient.networks.list.return_value = [mock_network]
        my_provider.name = "test_stack"
        my_provider.get_stack_parameters = mock.Mock()
        mystack = mock.Mock()
        mystack.outputs = [{'output_key': 'stdout',
                            'output_value': 'my output'}]
        my_provider.wait_for_status_changes = \
            mock.Mock(return_value=mystack)
        self.assertEqual(my_provider.launch_application(), None)
        self.assertTrue(my_provider._tester_stack)
        self.assertTrue(my_provider._application_stack)

    def test_register_floating_ips(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        mock_floating_ip = mock.Mock()
        mock_floating_ip.ip = '127.0.0.1'
        mock_floating_ip.instance_id = None
        my_provider._novaclient.floating_ips.list.return_value = [
            mock_floating_ip]

        test_res = my_provider.register_floating_ips(
            {"test_floating_ip": "127.0.0.1"})
        expected_parameters = {"floating_ip_test_floating_ip": "127.0.0.1"}
        self.assertDictEqual(my_provider.floating_ips, expected_parameters)
        self.assertDictEqual(test_res, {"test_floating_ip": "127.0.0.1"})

        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"pub_1": "1.2.3.4"})

    def test_register_static_floating_ips_already_reserved(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        my_provider._novaclient.floating_ips.list.return_value = []
        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"test_floating_ip": "127.0.0.1",
                           "test_floating_ip2": "127.0.0.1"})

    def test_register_static_floating_ips_already_used(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        mock_floating_ip = mock.Mock()
        mock_floating_ip.instance_id = "id"
        my_provider._novaclient.floating_ips.list.return_value = [
            mock_floating_ip]
        self.assertRaises(provider.FloatingIPError,
                          my_provider.register_floating_ips,
                          {"test_floating_ip": "127.0.0.1"})

    def test_register_dynamic_floating_ips_already_allocated(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        floating_ip_1 = mock.Mock()
        floating_ip_1.ip = "127.0.0.1"
        floating_ip_1.instance_id = None
        floating_ip_2 = mock.Mock()
        floating_ip_2.ip = "127.0.0.2"
        floating_ip_2.instance_id = None
        my_provider._novaclient.floating_ips.list.return_value = [
            floating_ip_1, floating_ip_2]
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
        my_provider._novaclient = mock.Mock()
        mock_floating_ips = []
        for i in range(1, 4):
            mock_floating_ip = mock.Mock()
            mock_floating_ip.ip = ('127.0.0.%d' % i)
            mock_floating_ip.instance_id = None
            mock_floating_ips.append(mock_floating_ip)
        my_provider._novaclient.floating_ips.list.return_value \
            = mock_floating_ips

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
        my_provider._novaclient = mock.Mock()
        mock_iface = mock.Mock()
        mock_iface.fixed_ips = [{'ip_address': '127.0.0.1'}]
        mock_server = mock.Mock()
        mock_server.name = 'robert-lapin'
        mock_server.interface_list.return_value = [mock_iface]
        my_provider._novaclient.servers.get.return_value = mock_server
        my_provider._heat = mock.Mock()

        mock_resource_1 = mock.Mock()
        mock_resource_1.resource_type = 'OS::Nothing::Here'
        mock_resource_2 = mock.Mock()
        mock_resource_2.resource_type = 'OS::Nova::Server'
        mock_resource_2.resource_name = 'nerf'
        mock_resource_2.physical_resource_id = 'lapin'
        my_provider._heat.resources.list.return_value = [
            mock_resource_1, mock_resource_2]

        my_provider._application_stack = provider.Stack("george", {})
        reference = {
            'nerf': {
                'id': 'lapin',
                'name': 'robert-lapin',
                'primary_ip_address': '127.0.0.1',
                'resource_name': 'nerf'
            }}
        self.assertEqual(reference, my_provider.get_machines())

    def test_filter_medias(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._glance = mock.Mock()
        mock_image_1 = mock.Mock()
        mock_image_1.name = "name_1"
        mock_image_1.id = 1
        mock_image_1.status = 'active'
        mock_image_1.filter_on = ['name']
        mock_image_3 = mock.Mock()
        mock_image_3.name = "name_3"
        mock_image_3.id = 3
        mock_image_3.status = 'killed'
        mock_image_3.filter_on = ['name', 'size']
        my_provider._glance.images.list.return_value = [
            mock_image_1, mock_image_3
        ]
        medias = {"name_1": mock_image_1,
                  "name_3": mock_image_3}
        to_up = my_provider._filter_medias(medias, ["name_2"])
        self.assertDictEqual(to_up, {"name_1": mock_image_1,
                                     "name_3": mock_image_3})

        # A local image
        mock_local_media = mock.Mock()
        mock_local_media.name = "name_1"
        mock_local_media.copy_from = False
        mock_local_media.generate.return_value = None
        medias = {"name_1": mock_local_media}
        my_provider._glance.images.get.return_value = mock_image_1

        with mock.patch('%s.open' % six.moves.builtins.__name__):
            actual_parameters = my_provider.upload(medias, ["name_1"])
        self.assertEqual(actual_parameters.keys(),
                         {'volume_id_name_1': None}.keys())  # Py34

        my_provider._glance.images.get.return_value = mock_image_3
        medias = {"name_1": mock_image_1}
        self.assertRaises(provider.ImageException,
                          my_provider.upload, medias, ["name_1"])
        self.assertEqual(actual_parameters.keys(),
                         {'volume_id_name_1': None}.keys())

    def _create_images_in_glance(self):
        img_in_glance = mock.Mock()
        img_in_glance.name = "name_1"
        img_in_glance.status = 'active'
        img_in_glance.disk_format = 'raw'
        img_in_glance.id = 1
        return [img_in_glance]

    def _create_images_to_upload(self):
        img_to_upload = mock.Mock()
        img_to_upload.name = "name_1"
        img_to_upload.disk_format = 'raw'
        img_to_upload.filter_on = ['name']
        img_to_upload.glance_id = None
        return {'name_1': img_to_upload}

    def test_filter_medias_by_status(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        images_in_glance[0].status = 'killed'
        my_provider._glance = mock.Mock()
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, None)

    def test_filter_medias_by_name(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        my_provider._glance = mock.Mock()
        # Match
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, 1)

    def test_filter_medias_by_name_dont_match(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        my_provider._glance = mock.Mock()
        # Don't match
        images_in_glance[0].name = "Michel"
        my_provider._glance = mock.Mock()
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, None)

    def test_filter_medias_by_name_size(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        my_provider._glance = mock.Mock()
        # Match
        images_in_glance[0].size = 10
        images_to_upload['name_1'].size = 10
        images_to_upload['name_1'].filter_on = ['name', 'size']
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, 1)

        # Don't match
        images_to_upload['name_1'].size = 11
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, 1)

    def test_filter_medias_by_checksum(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        my_provider._glance = mock.Mock()
        # Match
        images_in_glance[0].checksum = 'abc'
        images_to_upload['name_1'].checksum = 'abc'
        images_to_upload['name_1'].filter_on = ['checksum']
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, 1)

        # Don't match
        images_to_upload['name_1'].checksum = 'abcd'
        to_up = my_provider._filter_medias(
            images_to_upload,
            [])
        self.assertEqual(to_up['name_1'].glance_id, 1)

    def test_filter_medias_different_format(self):
        my_provider = provider.Heat(args=fake_args())
        images_in_glance = self._create_images_in_glance()
        images_to_upload = self._create_images_to_upload()
        my_provider._glance = mock.Mock()
        images_in_glance[0].disk_format = 'vmdk'
        my_provider._glance.images.list.return_value = images_in_glance
        to_up = my_provider._filter_medias(images_to_upload, [])
        self.assertEqual(to_up['name_1'].glance_id, None)

    def test__upload_medias_already_done(self):
        my_provider = provider.Heat(args=fake_args())
        my_media = mock.Mock()
        my_media.name = "Jim"
        my_media.glance_id = 123
        provider.LOG = mock.Mock()
        my_provider._upload_medias({'my_media': my_media})
        provider.LOG.info.assert_called_with('Jim already in Glance (123)')

    def test__upload_medias_with_copy_from(self):
        my_provider = provider.Heat(args=fake_args())
        my_media = mock.Mock()
        my_media.name = "Jim"
        my_media.copy_from = "http://somewhere"
        my_media.glance_id = None
        provider.LOG = mock.Mock()
        my_provider._glance = mock.Mock()
        my_provider._upload_medias({'my_media': my_media})
        provider.LOG.info.assert_called_with(
            "Downloading 'Jim' from http://somewhere")

    def test__upload_medias_with_local_image(self):
        my_provider = provider.Heat(args=fake_args())
        my_media = mock.Mock()
        my_media.name = "Jim"
        my_media.copy_from = None
        my_media.glance_id = None
        provider.LOG = mock.Mock()
        my_provider._glance = mock.Mock()
        tf = tempfile.NamedTemporaryFile()
        my_media.getPath.return_value = tf.name
        my_provider._upload_medias({'my_media': my_media})
        provider.LOG.info.assert_called_with(
            'Uploading %s to Jim' % tf.name)

    def test__wait_for_medias_in_glance(self):
        my_provider = provider.Heat(args=fake_args())
        my_media = mock.Mock()
        my_media.name = 'Kim'
        my_media.glance_id = 123
        my_provider._glance = mock.Mock()
        my_provider._glance.images.get.return_value = my_media
        self.assertEqual(my_provider._wait_for_medias_in_glance({}), {})

        provider.LOG = mock.Mock()
        my_media.status = 'active'
        my_provider._wait_for_medias_in_glance({'bob': my_media})
        provider.LOG.info.assert_called_with(
            'Image Kim is ready')

        my_media.status = 'killed'
        self.assertRaises(provider.ImageException,
                          my_provider._wait_for_medias_in_glance,
                          {'bob': my_media})
        provider.LOG.info.assert_called_with('Checking the image(s) status')

    @mock.patch('time.sleep', mock.Mock())
    def test__show_media_upload_status(self):
        MB = 1024 * 1024
        my_provider = provider.Heat(args=fake_args())
        fd = mock.Mock()
        fd.tell = mock.Mock()
        fd.tell.side_effect = [6 * MB, 12 * MB]
        provider.LOG = mock.Mock()
        size = 12 * MB
        my_provider._show_media_upload_status('foo', fd, size)
        provider.LOG.info.assert_called_with('foo:     6M /   12M')
        my_provider._show_media_upload_status('foo', fd, size)
        provider.LOG.info.assert_called_with('foo:    12M /   12M')

    def test_regiter_pub_key_ok(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        my_provider.register_pub_key('bob')
        self.assertEqual(
            my_provider.key_pairs,
            {'app_key_name': my_provider.name})

    def test_regiter_pub_key_dup(self):
        def keypairs_create_failure(name, key):
            raise novaclient.exceptions.Conflict("a", "b")

        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = mock.Mock()
        my_provider._novaclient.keypairs.create = keypairs_create_failure
        my_provider.register_pub_key('bob')
        self.assertEqual(
            my_provider.key_pairs,
            {'app_key_name': my_provider.name})

    def test_run(self):
        my_provider = provider.Heat(args=fake_args())
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
        my_provider._novaclient = mock.Mock()
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

    @mock.patch('time.sleep', mock.Mock())
    def test_wait_for_status_changes(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._heat = mock.Mock()

        mock_stack = mock.Mock()
        mock_stack.status = 'IN_PROGRESS'
        my_provider._heat.stacks.get.return_value = mock_stack
        my_provider._heat.events.list.return_value = []
        expected_status = ['CREATE_COMPLETE']
        self.assertRaises(provider.StackTimeoutException,
                          my_provider.wait_for_status_changes,
                          1,
                          expected_status)

        mock_stack.status = 'CREATE_COMPLETE'
        my_provider._heat.stacks.get.return_value = mock_stack
        my_provider._heat.events.list.return_value = []
        expected_status = ['CREATE_COMPLETE']
        stack = my_provider.wait_for_status_changes(1, expected_status)
        self.assertTrue(stack)

        mock_stack.status = 'FAILED'
        my_provider._heat.stacks.get.return_value = mock_stack
        my_provider._heat.events.list.return_value = []
        expected_status = ['CREATE_COMPLETE']
        self.assertRaises(provider.StackCreationFailure,
                          my_provider.wait_for_status_changes,
                          1,
                          expected_status)

    def test_cleanup_not_connected(self):
        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.cleanup(), None)

    def raise_ks_auth_failure(auth_url, username, password, tenant_name):
        raise keystoneexc.AuthorizationFailure()

    @mock.patch('keystoneclient.v2_0.Client', raise_ks_auth_failure)
    def test_connect_with_auth_failure(self):
        my_provider = provider.Heat(args=fake_args())
        self.assertRaises(mincer.exceptions.AuthorizationFailure,
                          my_provider.connect,
                          fake_identity)

    def test__show_stack_progress(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._heat = mock.Mock()
        entry1 = mock.Mock()
        entry1.resource_status = 'CREATE_IN_PROGRESS'
        entry1.resource_name = 'foo'
        my_provider._heat.events.list.return_value = [
            entry1
        ]
        provider.LOG = mock.Mock()
        my_provider._show_stack_progress(1)
        provider.LOG.info.assert_called_with('0: creating foo')
