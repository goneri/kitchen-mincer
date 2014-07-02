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

import fixtures
import mock
import tempfile
import testtools
import unittest

import mincer.providers.heat. provider as provider

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

    def url_for(self, service_type='fake_service'):

        return "http://somewhere/%s" % service_type


class fake_keystone(object):

    def __init__(self, **kwargs):

        self.service_catalog = fake_service_catalog()
        self.auth_token = "garantie_100%_truly_random"


class fake_novaclient(object):

    class fake_keypairs(object):
        def __init__(self, **kwargs):
            return

        def create(self, name, key):
            return True

    class fake_floating_ips(object):
        def __init__(self, **kwargs):
            return

        def list(self):
            return ()

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

    def __init__(self, **kwargs):
        self.keypairs = self.fake_keypairs()
        self.floating_ips = self.fake_floating_ips()
        self.servers = self.fake_servers()


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

        def get(self, stack_id):
            mockStack = mock.Mock()
            mockStack.outputs = [{
                'description': "foobar",
                'output_key': "stdout",
                'output_value': "my ouput"}]
            return mockStack

    def __init__(self, **kwargs):
        self.resources = self.fake_resources()
        self.stacks = self.fake_stacks()
        return


class fake_glanceclient(object):
    class fake_images(object):
        def __init__(self):
            self.fake_image_1 = mock.Mock()
            self.fake_image_1.name = "name_1"
            self.fake_image_1.id = "id_1"
            self.fake_image_2 = mock.Mock()
            self.fake_image_2.name = "name_2"
            self.fake_image_2.id = "id_2"

        def list(self):
            return [self.fake_image_1, self.fake_image_2]

    def __init__(self):
        self.images = self.fake_images()


class TestProvider(testtools.TestCase):
    def setUp(self):

        super(TestProvider, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('heatclient.v1.client.Client')
    def test_create(self, heat_mock):
        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.connect(fake_identity), None)
        self.assertEqual(my_provider.launch_application(
            "test_stack",
            {},
            {},
            {}), None)

    def test_register_key_pairs(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        t = my_provider.register_key_pairs({'robert': 'a_ssh_pub_key'})
        self.assertEqual(t['key_name'], 'robert')

    def test_register_floating_ips(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        self.assertRaises(provider.UnknownFloatingIP,
                          my_provider.register_floating_ips,
                          {'pub_ip': '::1'})

    def test_get_machines(self):
        my_provider = provider.Heat(args=fake_args())
        my_provider._novaclient = fake_novaclient()
        my_provider._heat = fake_heatclient()
        my_provider.application_stack_id = None
        result = [
            {
                'id': 'lapin',
                'name': 'robert-lapin',
                'primary_ip_address': '127.0.0.1',
                'resource_name': 'nerf'
            }
        ]
        self.assertEqual(my_provider.get_machines(), result)

    def test_filter_medias(self):
        my_provider = provider.Heat(args=fake_args())
        medias = {"name_1": "", "name_2": "", "name_3": ""}
        to_up, to_not_up = my_provider._filter_medias(fake_glanceclient(),
                                                      medias,
                                                      ["name_2"])

        res_to_up = {"name_2": None, "name_3": None}
        res_to_not_up = {"name_1": "id_1"}
        self.assertDictEqual(to_up, res_to_up)
        self.assertDictEqual(to_not_up, res_to_not_up)

if __name__ == '__main__':
    unittest.main()
