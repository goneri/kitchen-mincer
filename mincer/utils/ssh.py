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
import socket
import time

import paramiko
import six

LOG = logging.getLogger(__name__)

MAX_RETRY = 40


class SSH(object):

    """paramiko abstraction class."""

    def __init__(self, priv_key=None):
        """SSH class constructor."""
        self._ssh_client = None
        self._gateway_ip = None
        self._set_priv_key(priv_key)

    def _set_priv_key(self, priv_key):
        """Register the SSH private key."""
        try:
            stream = six.StringIO(priv_key.decode('UTF-8'))
        except AttributeError:  # Py27
            stream = six.StringIO(priv_key)
        self._raw_priv_key = stream
        self._priv_key = paramiko.RSAKey.from_private_key(stream)

    def get_user_config(self, hostname):
        """Load the user ssh configuration file."""
        ssh_config = paramiko.SSHConfig()
        user_config_file = os.path.expanduser("~/.ssh/config")
        if os.path.exists(user_config_file):
            with open(user_config_file) as f:
                ssh_config.parse(f)
        return ssh_config.lookup(hostname)

    def _try_start_ssh_client(self, client, cfg, user_config):
        for retry in six.moves.range(0, MAX_RETRY):
            try:
                LOG.info("Trying to open the SSH tunnel...")
                if 'proxycommand' in user_config:
                    LOG.debug("proxycommand found in SSH user configuration")
                    cfg['sock'] = paramiko.ProxyCommand(
                        user_config['proxycommand'])
                client.connect(**cfg)
                self._ssh_client = client
                break
            except socket.error as e:
                LOG.debug(e)
            except paramiko.ssh_exception.SSHException as e:
                LOG.debug(e)
            time.sleep(5)
            LOG.info("retrying")
        if (retry + 1) >= MAX_RETRY:
            raise AuthOverSSHTransportError()

    def start_transport(self, gateway_ip):
        """Start the ssh tunnel between the mincer and the gateway."""
        self._gateway_ip = gateway_ip
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)
        client = paramiko.SSHClient()
        client._policy = paramiko.WarningPolicy()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        cfg = {'hostname': gateway_ip, 'username': 'ec2-user', 'timeout': 10}

        LOG.info("Gateway IP: '%s'" % cfg['hostname'])
        user_config = self.get_user_config(cfg['hostname'])
        for k in ('hostname', 'username', 'port'):
            if k in user_config:
                cfg[k] = user_config[k]

        cfg['pkey'] = self._priv_key
        self._try_start_ssh_client(client, cfg, user_config)
        sftp = paramiko.SFTPClient.from_transport(
            self.get_transport())
        id_rsa = sftp.open('/home/ec2-user/.ssh/id_rsa', 'w')
        id_rsa.write(self._raw_priv_key.getvalue())
        sftp.chmod('/home/ec2-user/.ssh/id_rsa', 0o600)
        LOG.info("SSH transport is ready")

    def get_transport(self, host_ip=None):
        """Open a session from the existing SSH transport.

        The SSH transport has to be created first with start_transport()

        """
        if host_ip is not None:
            for retry in six.moves.range(0, MAX_RETRY):
                try:
                    LOG.info("Trying to open the SSH session...")
                    channel = self._ssh_client.get_transport().open_channel(
                        'direct-tcpip',
                        (host_ip, 22),
                        (self._gateway_ip, 0))

                    t = paramiko.Transport(channel)
                    t.start_client()

                    t.auth_publickey('ec2-user', self._priv_key)
                    break
                except paramiko.ssh_exception.SSHException:
                    time.sleep(30)
                    LOG.info("Retrying")
            if (retry + 1) >= MAX_RETRY:
                raise AuthOverSSHTransportError()
        else:
            # Open a session directly on the Gateway
            t = self._ssh_client.get_transport()

        return t


class AuthOverSSHTransportError(Exception):

    """Raised when the client failed to connect throught the SSH transport."""
