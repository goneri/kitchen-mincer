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

import mincer.provider

import mock
import testtools


class TestProvider(testtools.TestCase):
    def test_get_provider(self):
        env = mock.Mock()
        env.provider_params.return_value = {}
        env.provider.return_value = "heat"
        my_provider = mincer.provider.get(env)
        self.assertIsInstance(my_provider, mincer.providers.heat.provider.Heat)

    @mock.patch('mincer.providers.heat.provider.Heat.__init__')
    def test_get_provider_report_error(self, mocked_heat_init):
        env = mock.Mock()
        mocked_heat_init.return_value = False
        mincer.provider.LOG = mock.Mock()
        env.provider_params.return_value = {}
        env.provider.return_value = "heat"
        self.assertRaises(
            TypeError,
            mincer.provider.get,
            env)
        mincer.provider.LOG.error.assert_called()
