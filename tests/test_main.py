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
env1:
  method: fakemethod
  heat-file: heat.yaml
  identity: identity.yaml
  enabled: no

  arbitary-configuration: hello
"""

SAMPLE_IDENTITY = """---
samplecloud:
  os_username: $CHOCOLATE
  os_tenant_name: tenant
  os_password: password
  os_auth_url: http://os.enocloud.com:5000/v2.0
"""


class TestMain(testtools.TestCase):
    def setUp(self):
        super(TestMain, self).setUp()
        self.testdir = self.useFixture(fixtures.TempDir()).path

        with open(os.path.join(self.testdir, "marmite.yaml"), 'w') as f:
            f.write(SAMPLE_MARMITE)
        os.makedirs(os.path.join(self.testdir, "identities"))
        with open(os.path.join(
                self.testdir, "identities", "identity.yaml"), 'w') as f:
            f.write(SAMPLE_IDENTITY)

    def test_basic_init(self):
        m = mixer.Mixer(self.testdir)
        self.assertIn('env1', m.yaml_tree.keys())

    def test_init_no_marmite(self):
        self.assertRaises(exceptions.NotFound,
                          mixer.Mixer, "/NOTHERE")

    def test_inexistent_provider(self):
        m = mixer.Mixer(self.testdir)
        self.assertRaises(RuntimeError,
                          m.start_provider, "env1")

    def test_get_identity(self):
        env = 'env1'
        m = mixer.Mixer(self.testdir)
        ret = m.get_identity(env)
        self.assertIn("samplecloud", ret)
        cloud = ret['samplecloud']
        for x in ('os_password', 'os_password', 'os_password', 'os_username'):
            self.assertIn(x, cloud)

    def test_get_identity_with_shell_variable(self):
        with mock.patch.dict('os.environ', {'CHOCOLATE': 'FACTORY'}):
            env = 'env1'
            m = mixer.Mixer(self.testdir)
            ret = m.get_identity(env)
            self.assertEqual(ret['samplecloud']['os_username'], 'FACTORY')

    def test_get_identity_with_unkown_shell_variable(self):
        with mock.patch.dict('os.environ', {}):
            env = 'env1'
            m = mixer.Mixer(self.testdir)
            ret = m.get_identity(env)
            self.assertIsNone(ret['samplecloud']['os_username'])
