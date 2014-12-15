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

import logging

import mock
import testtools

import mincer.utils.logger


class TestLogger(testtools.TestCase):

    def setUp(self):
        super(TestLogger, self).setUp()
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.auth_args = {
            'user': 'admin',
            'key': 'password',
            'authurl': 'http://somewhere:5000/v2.0',
            'tenant_name': 'admin',
            'auth_version': '2.0'}

    @mock.patch('swiftclient.client.Connection')
    def test_flush(self, swift):
        swift_cnx = mock.Mock()
        swift.return_value = swift_cnx
        logHandler = mincer.utils.logger.RotatingSwiftHandler(self.auth_args)
        self.logger.addHandler(logHandler)
        self.logger.info("Bibi")
        logHandler.flush()
        swift_cnx.put_object.assert_called_once_with('log', 'name-00', 'Bibi')

    @mock.patch('swiftclient.client.Connection')
    def test_capacity(self, swift):
        swift_cnx = mock.Mock()
        swift.return_value = swift_cnx
        logHandler = mincer.utils.logger.RotatingSwiftHandler(
            self.auth_args, capacity=1)
        self.logger.addHandler(logHandler)
        self.logger.info("Bibi")
        self.logger.info("Bibi")
        logHandler.flush()
        swift_cnx.put_object.assert_has_calls([
            mock.call('log', 'name-00', 'Bibi'),
            mock.call('log', 'name-01', 'Bibi')])

    @mock.patch('swiftclient.client.Connection')
    def test_flushlevel(self, swift):
        swift_cnx = mock.Mock()
        swift.return_value = swift_cnx
        logHandler = mincer.utils.logger.RotatingSwiftHandler(
            self.auth_args, flushLevel=logging.INFO)
        self.logger.addHandler(logHandler)
        self.logger.info("Bibi")
        self.logger.info("Bibi")
        logHandler.flush()
        swift_cnx.put_object.assert_has_calls([
            mock.call('log', 'name-00', 'Bibi'),
            mock.call('log', 'name-01', 'Bibi')])
