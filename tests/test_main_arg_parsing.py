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
import testtools

import mincer.main


class TestMain(testtools.TestCase):

    def test_arg_parsing(self):
        mincer.main.setup_logging = mock.Mock()
        mincer.main.bootstrap = mock.Mock()
        mincer.main.main(["foo",
                          "--marmite_directory", "./tests/test_marmite",
                          "--debug",
                          "--extra_params", "foo:bar,foot:ball",
                          "--credentials_file", "/tmp/somewhere",
                          "--refresh_medias", "media1,media2",
                          "--preserve"])
        self.assertEqual(mincer.main.CONF.marmite_directory,
                         "./tests/test_marmite")
        self.assertEqual(mincer.main.CONF.debug,
                         True)
        self.assertEqual(mincer.main.CONF.extra_params,
                         {'foot': 'ball', 'foo': 'bar'})
        self.assertEqual(mincer.main.CONF.credentials_file,
                         "/tmp/somewhere")
        self.assertEqual(mincer.main.CONF.refresh_medias,
                         ["media1", "media2"])
        self.assertEqual(mincer.main.CONF.preserve,
                         True)
