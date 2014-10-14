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

import tempfile

import mincer.utils.ssh

import fixtures
import mock
import paramiko.ssh_exception
import testtools


priv_key = (
    '-----BEGIN RSA PRIVATE KEY-----\n'
    'MIIEowIBAAKCAQEAzs85GKWXwwV+vvYX6j1rEzcH9KHhCn7JMJBK+FTJqUAF3apA\n'
    'Zjfhp8vp9EQ3O7A+QES5gupucQ3JM2vWXGiXKLghjkUQfqMj5dbv9a86QfBOngcE\n'
    'Uns4tKEnekBju6W0B3mPCUpUDW36N10syWAV3mhyT4ru0WtsBMMQvuEgaSWL3ZdR\n'
    'hFtgzp2xoJE5GE1YrUpbLw7VEZ2g4ftsKGQynomkTe4waH9NO/k5Yi53BiJbyXei\n'
    'ZdrFPQYyaKKeovrps8WwBATHNF8VhzFuH+gLnM1ceD7AxUZgPSlrTMCPJfIew6Y4\n'
    '75l0jRyYyRGITcHchSrZAoQFUDqum7AZg0FgdwIDAQABAoIBAAxkYGB4s7JM5v5c\n'
    'UqyHh538Iy7mcEynsjiFvOhKdFb+7hsNM5SsbooWbutjFwgtlF1XgOI2V+3QTKkX\n'
    'Ih4hakVXWzNiMg3Uircf/Pr0yAHhe2R+uSSUG56/NVVe/FrnH/V+tDJzULwJRgAB\n'
    'Rki+yDCug4L+qTbFQBC8+4jkhoOmT6CEo9F1a77APl/yhRoVLiW3MGKH9XxOlHC6\n'
    'Zu6+IIFl87/ChSrrHTOyUfmgJxPFg+z5IiPxGCnac9PkolCNXtSz0Ogpf9c/3BiK\n'
    '69JoykgbS0fB7ViVEz8acpif6j4EPtC70WViwrUgMxEvLhEjAjGODkTBr9Yc3WBY\n'
    '4ukO6WkCgYEA0wJ+7Q5F9iz1zTpOcbyk16QtJnIe4rWv5OkhAMuU4fsiyMFcJUQ5\n'
    'v7oleWOCtDFzBf2HiDURV3vVXgSquh4N3IBCYB2Mylm35QwLUfetcWoZ4ej04qCP\n'
    'lY5ffQ3yYfnDonK6nzFe2IxjSE0zOX96Ru5A2hd3ib0fI7xOHlFiXQ0CgYEA+ud2\n'
    'w+R/26jDIh8lT03zMksQbBozjB/RyMtcbgagCUlYT4pWI48qGZy3afKq7ta7euxE\n'
    'pV2fPn7aR0wk3CmuUGg1kPYFxm/kUJfle7QmvVePmWQekzUMl7FZ451cwUm+9PvO\n'
    'c8oVUJXy/qVQHNmNcjhOubLsXud7iPfgf2c1OpMCgYEAn9yNMqWUpWvskR4yXgLQ\n'
    'VDsipbTh51pEt0VT5plV41rzQGsVl3o30iSBzZRxanjoLsqkCrJBwCimPsOEYNry\n'
    'H3LgVpcsmgUcyB+219OwCHOcxkVKegOwpFqnx0NwtX+XEpSfBIpP0/mQIi+ytkX4\n'
    '6pIIefI7cxPf6p/4AwofXmUCgYAvruOUUQ23ijgjePXXP4Izka56TPR08esllPho\n'
    '9JtfiG/fFfRO57thiLYWzYaMw4R31QUqxEMqVmNXX3I14Tn+j/92IDtyvfsPEf8L\n'
    '5m3iWAyzYyKoaVGOVqc1qcdh+Ijw+BYBTWuFmCnJGVPDV9kY1vinNAjV9Ho2yp0A\n'
    'uXWVPwKBgDX+endQA6C064lQoJwzET1HtyH7N3M5D+4BK1Ru1OgRBlbKax1lajaR\n'
    'vZKH626ZZ+XH/Ph1VR4s8UZMytWFflLGT7VCe50jVLwBTCD5fkRGDhb4BA3BKFWR\n'
    'PjASBWf1hRiQWQg0WeGkkG+cPSbUOcZu00oV/8jkucTcbw9/L1z/\n'
    '-----END RSA PRIVATE KEY-----')


class TestSSH(testtools.TestCase):
    def setUp(self):
        super(TestSSH, self).setUp()
        self.ssh = mincer.utils.ssh.SSH(priv_key)

    def test__set_priv_key(self):
        self.assertTrue(self.ssh._priv_key)
        self.useFixture(fixtures.NestedTempfile())

    @mock.patch('paramiko.config.SSHConfig.lookup',
                mock.Mock(return_value=True))
    def test_get_user_config(self):
        with tempfile.NamedTemporaryFile() as config:
            config.write(bytearray('Host noah ProxyCommand foo\n', 'UTF-8'))
            config.seek(0)
            self.assertTrue(self.ssh.get_user_config('noah'))

    @mock.patch('paramiko.client.SSHClient.connect',
                mock.Mock(return_value=True))
    @mock.patch('paramiko.SFTPClient.from_transport',
                mock.Mock())
    def test_start_transport(self):
        # without user_config
        self.ssh.get_user_config = mock.Mock(return_value={})
        self.get_transport = mock.Mock()
        self.ssh.start_transport('127.0.0.1')
        self.ssh._ssh_client.connect.assert_called_with(
            hostname='127.0.0.1',
            pkey=self.ssh._priv_key,
            username='ec2-user',
            timeout=10)

        # Now with user_config
        self.ssh._ssh_client = None
        user_config = {
            'hostname': 'a',
            'username': 'robert',
            'port': 0,
            'proxycommand': '/bin/cat'
        }
        self.ssh.get_user_config = mock.Mock(return_value=user_config)
        self.ssh.start_transport('127.0.0.1')
        self.assertTrue(self.ssh._ssh_client.connect.called, True)

    def test_get_transport_no_gateway(self):
        self.ssh._ssh_client = mock.Mock()
        self.ssh._ssh_client.return_value = mock.Mock()
        self.assertTrue(self.ssh.get_transport(None))

    @mock.patch('paramiko.transport.Transport.open_session', mock.Mock())
    @mock.patch('paramiko.transport.Transport.start_client', mock.Mock())
    @mock.patch('paramiko.transport.Transport.auth_publickey', mock.Mock())
    def test_get_transport_with_gateway(self):
        self.ssh._ssh_client = mock.Mock()
        self.ssh._ssh_client.return_value = mock.Mock()
        self.assertTrue(self.ssh.get_transport('127.0.0.1'))

    def raise_ssh_exception(arg1, arg2, arg3):
        raise paramiko.ssh_exception.SSHException()

    @mock.patch('paramiko.transport.Transport.open_session', mock.Mock())
    @mock.patch('paramiko.transport.Transport.start_client', mock.Mock())
    @mock.patch('paramiko.transport.Transport.auth_publickey',
                raise_ssh_exception)
    @mock.patch('time.sleep', mock.Mock())
    def test_get_transport_max_retry(self):
        self.ssh._ssh_client = mock.Mock()
        self.ssh._ssh_client.return_value = mock.Mock()
        self.assertRaises(mincer.utils.ssh.AuthOverSSHTransportError,
                          self.ssh.get_transport,
                          '127.0.0.1')
