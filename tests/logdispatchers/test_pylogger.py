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

import unittest

import mock
import six
import testtools

import mincer.logdispatchers.pylogger. logdispatcher as logdispatcher


class TestLogdispatcher(testtools.TestCase):
    def setUp(self):
        super(TestLogdispatcher, self).setUp()
        self.ld = logdispatcher.PyLogger({}, None)

    def test_store(self):
        logdispatcher.LOG = mock.Mock()
        blabla = "some initial text data"
        f = six.StringIO(blabla)
        self.ld.store('robert', f)
        logdispatcher.LOG.info.assert_called_with("some initial text data")

if __name__ == '__main__':
    unittest.main()
