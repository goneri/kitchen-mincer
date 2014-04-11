# -*- coding: utf-8 -*-
# Author: eNovance developers <dev@enovance.com>
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

from mincer import marmite

import mock
import testtools


class TestMarmite(testtools.TestCase):

    def setUp(self):
        super(TestMarmite, self).setUp()
        self.marmite = marmite.Marmite("./tests/test_files")
        self.environments = self.marmite.environments()
        self.application = self.marmite.application()

    def test_fake_marmite_init(self):
        self.assertRaises(ValueError, marmite.Marmite, None)
        self.assertRaises(marmite.NotFound, marmite.Marmite, "/tmp")

    def test_description(self):
        self.assertEqual("A wordpress in a container (web and DB)",
                         self.marmite.description())

    def test_environment_provider(self):
        self.assertIn("heat-devstack-docker",
                      self.environments.provider("devtest"))
        provider_params = self.environments.provider_params("devtest")
        self.assertIn("heat-devstack-docker", provider_params["image"])
        self.assertIn("m1.medium", provider_params["flavor"])
        self.assertIn("Nopasswd", provider_params["keypair"])
        self.assertIn("46.231.128.152", provider_params["floating_ip"])

    def test_inexistent_environment(self):
        self.assertRaises(marmite.NotFound,
                          self.marmite.environments().provider,
                          "fake_env")

    def test_identity(self):

        with mock.patch.dict('os.environ', {'OS_TENANT_NAME': 'tenant',
                                            'OS_AUTH_URL': 'auth_url'}):
            devtest_identity = self.environments.identity("devtest")

            self.assertEqual("bob_l_eponge", devtest_identity["os_username"])
            self.assertEqual("password", devtest_identity["os_password"])
            self.assertEqual("tenant", devtest_identity["os_tenant_name"])
            self.assertEqual("auth_url", devtest_identity["os_auth_url"])

    def test_identity_with_unknown_env_variables(self):
        with mock.patch.dict('os.environ', {}):
            self.assertRaises(ValueError,
                              self.environments.identity,
                              "devtest")

    def test_pool(self):
        ip_pool_devtest = self.environments.ip_pool("devtest")
        self.assertIn("10.0.0.4", ip_pool_devtest)
        self.assertIn("10.0.0.5", ip_pool_devtest)
        self.assertIn("10.0.0.6", ip_pool_devtest)

    def test_application(self):
        self.assertEqual("wordpress", self.application.name())
        self.assertIsNotNone(self.application.params())
        self.assertIsNotNone(self.application.medias())

    def test_params(self):
        params = self.application.params()

        params_expected = {"type": "floating_ip",
                           "name": "mysql_server", "idx": 0}
        self.assertDictEqual(params_expected, params[0])

        params_expected = {"type": "floating_ip",
                           "name": "mysql_server", "idx": 0}
        self.assertDictEqual(params_expected, params[0])

        params_expected = {"type": "media", "name": "wp_files"}
        self.assertDictEqual(params_expected, params[4])
        self.assertIn("wp_files", self.application.medias())
