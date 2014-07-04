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
import six
import testtools
import unittest

import mincer.logdispatchers.swift. logdispatcher as logdispatcher


class TestLogdispatcher(testtools.TestCase):
    def setUp(self):

        super(TestLogdispatcher, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    def test__get_full_path(self):
        provider = mock.Mock()
        provider.put_object.value = True
        ld = logdispatcher.Swift({'path_template': 'toto/$name'}, provider)
        self.assertEqual(ld._get_full_path("zozo"), "toto/zozo")

    def test_store(self):
        blabla = "some initial text data"
        provider = mock.Mock()
        provider.put_object.value = True
        ld = logdispatcher.Swift({}, provider)
        f = six.StringIO(blabla)
        self.assertEqual(ld.store('robert.log', f), None)


if __name__ == '__main__':
    unittest.main()
