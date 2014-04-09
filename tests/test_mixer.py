# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel.boudjnah@enovance.com>
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
import os

import fixtures
import mock
import testtools

from mincer import exceptions
from mincer import mixer


SAMPLE_MARMITE = """---
environments:
  env1:
    method: fakemethod
    identity: fakeident
    heat-file: heat.yaml

methods:
  fakemethod:
    enabled: no
    arbitary_configuration: hello

identities:
  fakeident:
    os_username: $CHOCOLATE
    os_tenant_name: tenant
    os_password: password
    os_auth_url: http://os.enocloud.com:5000/v2.0
"""

SAMPLE_IDENTITY = """
"""


class TestMixer(testtools.TestCase):
    def setUp(self):
        super(TestMixer, self).setUp()
        self.testdir = self.useFixture(fixtures.TempDir()).path

        with open(os.path.join(self.testdir, "marmite.yaml"), 'w') as f:
            f.write(SAMPLE_MARMITE)
        os.makedirs(os.path.join(self.testdir, "identities"))
        with open(os.path.join(
                self.testdir, "identities", "identity.yaml"), 'w') as f:
            f.write(SAMPLE_IDENTITY)

        self.mixer = mixer.Mixer(self.testdir, {})

    def test_basic_init(self):
        self.assertIn('env1', self.mixer.yaml_tree['environments'])

    def test_init_no_marmite(self):
        self.assertRaises(exceptions.NotFound,
                          mixer.Mixer, "/NOTHERE", {})

    def test_inexistent_provider(self):
        self.assertRaises(RuntimeError,
                          self.mixer.start_provider, "env1")

    def test_get_identity(self):
        env = 'env1'
        ret = self.mixer.get_identity(env)
        for x in ('os_password', 'os_password', 'os_password', 'os_username'):
            self.assertIn(x, ret)

    def test_get_identity_with_shell_variable(self):
        with mock.patch.dict('os.environ', {'CHOCOLATE': 'FACTORY'}):
            env = 'env1'
            self.assertEqual(self.mixer.get_identity(env)['os_username'],
                             'FACTORY')

    def test_get_identity_with_unkown_shell_variable(self):
        with mock.patch.dict('os.environ', {}):
            env = 'env1'
            self.assertIsNone(self.mixer.get_identity(env)['os_username'])

    def test_provider_not_here(self):
        self.assertRaises(exceptions.NotFound,
                          self.mixer._check_provider_is_here, "FOO")

    def test_get_method_configuration(self):
        ret = self.mixer.get_method_configuration("fakemethod")
        self.assertIn('enabled', ret)
        self.assertIn('arbitary_configuration', ret)

    #TODO(chmou): Test individual files get methods
    def test_get_method_configuration_file(self):
        self.skipTest("Not tested yet")

    #TODO(chmou): Test individual files get methods
    def test_get_identity_configuration_file(self):
        self.skipTest("Not tested yet")
