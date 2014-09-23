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
import os
import time

import paramiko
import six

LOG = logging.getLogger(__name__)


class SSH(object):
    def __init__(self, priv_key=None):
        self._ssh_client = None
        self._gateway_ip = None
        self._set_priv_key(priv_key)

    def _set_priv_key(self, priv_key):
        # TODO(Gonéri): do we still need this method ...
        keyfile = six.StringIO(priv_key.replace('\\n', "\n"))
        self._priv_key = paramiko.RSAKey.from_private_key(keyfile)
#        self._priv_key.write_private_key_file('/tmp/current.key')
#        print("done")

    def get_user_config(self, hostname):
        ssh_config = paramiko.SSHConfig()
        user_config_file = os.path.expanduser("~/.ssh/config")
        if os.path.exists(user_config_file):
            with open(user_config_file) as f:
                ssh_config.parse(f)
        return ssh_config.lookup(hostname)

    def start_transport(self, gateway_ip):
        self._gateway_ip = gateway_ip
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)
        client = paramiko.SSHClient()
        client._policy = paramiko.WarningPolicy()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        cfg = {'hostname': gateway_ip, 'username': 'ec2-user'}

        LOG.info("Gateway IP: '%s'" % cfg['hostname'])
        user_config = self.get_user_config(cfg['hostname'])
        for k in ('hostname', 'username', 'port'):
            if k in user_config:
                cfg[k] = user_config[k]

        cfg['pkey'] = self._priv_key

        while self._ssh_client is None:
            try:
                LOG.info("Trying to open the SSH tunnel...")
                if 'proxycommand' in user_config:
                    cfg['sock'] = paramiko.ProxyCommand(
                        user_config['proxycommand'])
                client.connect(**cfg)
                self._ssh_client = client
            except paramiko.ssh_exception.SSHException:
                time.sleep(5)
        LOG.info("SSH transport is ready")

    def open_session(self, host_ip=None):
        if host_ip is not None:
            transport = self._ssh_client.get_transport()
            channel = None
            while channel is None:
                try:
                    channel = transport.open_channel(
                        'direct-tcpip',
                        (host_ip, 22),
                        (self._gateway_ip, 0))
                except paramiko.ssh_exception.ChannelException:
                    time.sleep(5)
            t = paramiko.Transport(channel)
            t.start_client()

            auth_ok = None
            while auth_ok is None:
                try:
                    LOG.info("Trying to open the SSH session...")
                    t.auth_publickey('ec2-user', self._priv_key)
                    auth_ok = 1
                except paramiko.ssh_exception.SSHException:
                    time.sleep(30)

            session = t.open_session()
        else:
            # Open a session directly on the Gateway
            session = self._ssh_client.get_transport().open_session()

        return session
