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

import logging

import fixtures
import testtools

from mincer import marmite


class TestMarmite(testtools.TestCase):

    def setUp(self):
        super(TestMarmite, self).setUp()
        self.useFixture(fixtures.NestedTempfile())
        self.marmite = marmite.Marmite("./tests/test_marmite")
        self.application = self.marmite.application()

    def test_fake_marmite_init(self):
        self.assertRaises(ValueError, marmite.Marmite, None)
        self.assertRaises(marmite.NotFound, marmite.Marmite, "/tmp")

    def test_description(self):
        self.assertEqual("a sample marmite",
                         self.marmite.description())

    def test_environment_provider(self):
        self.assertIn("heat-devstack-docker",
                      self.marmite.environment("devtest").provider())
        provider_params = self.marmite.environment("devtest").provider_params()
        self.assertIn("heat-devstack-docker", provider_params["image"])
        self.assertIn("m1.medium", provider_params["flavor"])
        self.assertIn("Nopasswd", provider_params["keypair"])
        self.assertIn("46.231.128.152", provider_params["floating_ip"])
        fake_env = marmite.Environment("fake_env", {})
        self.assertIn("heat", fake_env.provider())

    def test_application(self):
        self.assertEqual("wordpress", self.application.name())
        self.assertIsNotNone(self.application.scenario())

    def test_marmite_bad_template(self):
        logging.disable(logging.CRITICAL)
        self.assertRaises(marmite.InvalidStructure,
                          marmite.Marmite,
                          "./tests/test_marmite_bad_template")

    def test_marmite_missing_keys(self):
        self.assertRaises(marmite.InvalidStructure,
                          marmite.Marmite,
                          "./tests/test_marmite_missing_keys")
