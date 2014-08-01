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

import os
import tempfile
import unittest

import fixtures
import mock
import six
import testtools

import mincer.logdispatchers.directory. logdispatcher as logdispatcher


class TestLogdispatcher(testtools.TestCase):
    def setUp(self):
        self.provider = mock.Mock()
        super(TestLogdispatcher, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    def test_create(self):
        tmpdir = tempfile.mkdtemp()
        ld = logdispatcher.Directory({'directory': tmpdir}, self.provider)
        self.assertIsInstance(ld, logdispatcher.Directory)
        self.assertTrue(os.path.exists(tmpdir))

    def test_store(self):
        blabla = "some initial text data"
        tmpdir = tempfile.mkdtemp()
        ld = logdispatcher.Directory({'path': tmpdir}, self.provider)
        f = six.StringIO(blabla)
        ld.store('robert', f)
        self.assertEqual(
            open(os.path.join(tmpdir, 'robert.log')).read(),
            blabla)


if __name__ == '__main__':
    unittest.main()
