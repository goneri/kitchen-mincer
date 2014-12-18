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

import mock
from oslo.config import fixture as fixture_config
import testtools

import mincer.main


class TestMain(testtools.TestCase):

    def setUp(self):
        super(TestMain, self).setUp()
        mincer.main.CONF = self.useFixture(fixture_config.Config()).conf

    @mock.patch('mincer.credentials')
    @mock.patch('mincer.provider')
    @mock.patch('mincer.marmite')
    def test_bootstrap(self, marmite, provider, credentials):
        marmite_directory = "./tests/test_marmite"
        mincer.main.CONF.set_override(
            'marmite_directory', marmite_directory)
        mincer.main.CONF.set_override(
            'credentials_file', 'nowhere')

        my_provider = mock.Mock()
        my_credentials = mock.Mock()
        my_credentials.get.return_value = 'my credentials'
        provider.get.return_value = my_provider
        credentials.Credentials.return_value = my_credentials

        mincer.main.bootstrap()
        marmite.Marmite.assert_called_with(marmite_directory=marmite_directory)
        my_provider.connect.assert_called_with('my credentials')
