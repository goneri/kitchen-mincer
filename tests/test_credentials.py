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

import tempfile
import unittest

import fixtures
import mock
import testtools
import voluptuous

import mincer.credentials

reference = {
    'os_auth_url': 'a',
    'os_username': 'b',
    'os_password': 'c',
    'os_tenant_name': 'd'}


class TestCredentials(testtools.TestCase):
    def setUp(self):
        super(TestCredentials, self).setUp()
        self.useFixture(fixtures.NestedTempfile())
        with mock.patch('mincer.credentials.Credentials.__init__') as my_init:
            my_init.return_value = None
            self.c = mincer.credentials.Credentials()

    def test__get_from_file(self):
        file_loc = tempfile.mkdtemp() + "/file.yaml"
        with open(file_loc, "w") as credentials_file:
            credentials_file.write('os_auth_url: bob')
        self.assertEqual(self.c._get_from_file(file_loc),
                         {'os_auth_url': 'bob'})

    def test__get_from_environ(self):
        self.assertEqual(self.c._get_from_environ(),
                         {'os_auth_url': '$OS_AUTH_URL',
                          'os_username': '$OS_USERNAME',
                          'os_password': '$OS_PASSWORD',
                          'os_tenant_name': '$OS_TENANT_NAME'})

    def test__validate_credentials(self):
        self.assertRaises(voluptuous.MultipleInvalid,
                          self.c._validate_credentials,
                          'rob')
        self.assertEqual(self.c._validate_credentials(reference),
                         None)

    def test__expand_credentials(self):
        with mock.patch.dict('os.environ', {'OS_AUTH_URL': 'aa'}):
            t = self.c._expand_credentials({'aze': '$OS_AUTH_URL'})
            self.assertEqual(t, {'aze': 'aa'})

    def test__expand_credentials_missing_env_key(self):
        self.assertRaises(ValueError,
                          self.c._expand_credentials,
                          {'aze': '$OS_FOO'})

    def test__init__missing_file(self):
        self.assertRaises(IOError,
                          self.c.__init__,
                          '/nowhere')

    @mock.patch('os.path.exists')
    def test__init__load_default_file(self, mocked_path_exists):
        def my_get_from_file(a):
            return(reference)

        mocked_path_exists.return_value = True
        self.c._get_from_file = my_get_from_file
        self.c.__init__(None)
        self.assertEqual(self.c.credentials, reference)

    @mock.patch('os.path.exists')
    def test__init__load_environ(self, mocked_path_exists):
        def my_get_environ():
            return(reference)

        mocked_path_exists.return_value = False
        self.c._get_from_environ = my_get_environ
        self.c.__init__(None)
        self.assertEqual(self.c.credentials, reference)

    def test__init__from_file(self):
        file_loc = tempfile.mkdtemp() + "/file.yaml"
        with open(file_loc, "w") as credentials_file:
            credentials_file.write("os_auth_url: a\n"
                                   "os_username: b\n"
                                   "os_password: c\n"
                                   "os_tenant_name: d")
        self.c.__init__(file_loc)
        self.assertEqual(self.c.credentials,
                         {'os_password': 'c', 'os_auth_url': 'a',
                          'os_username': 'b', 'os_tenant_name': 'd'})

    def test_get(self):
        expected = {'bob': 'bib'}
        self.c.credentials = expected
        self.assertEqual(expected, self.c.get())


if __name__ == '__main__':
    unittest.main()
