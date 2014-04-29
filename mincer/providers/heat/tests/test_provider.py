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

        self.marmite_directory = tempfile.mkdtemp()
        with open(self.marmite_directory + "/heat.yaml", 'w') as f:
            f.write("""
heat_template_version: 2013-05-23

description: >
  Yet another useless Heat template.
""")


class fake_service_catalog():

    def url_for(self, service_type='fake_service'):

        return "http://somewhere/%s" % service_type


class fake_keystone():

    def __init__(self, **kwargs):

        self.service_catalog = fake_service_catalog()
        self.auth_token = "garantie_100%_truly_random"


class TestProvider(testtools.TestCase):
    def setUp(self):

        super(TestProvider, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    def test_get_heat_template(self):

        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.connect(fake_identity), None)
        heat_template = my_provider._get_heat_template()
        self.assertRegexpMatches(heat_template, ".*useless\ Heat\ template.*")

    @mock.patch('keystoneclient.v2_0.Client', fake_keystone)
    @mock.patch('heatclient.v1.client.Client')
    def test_create(self, heat_mock):
        my_provider = provider.Heat(args=fake_args())
        self.assertEqual(my_provider.connect(fake_identity), None)
        self.assertEqual(my_provider.create(), None)

if __name__ == '__main__':
    unittest.main()
