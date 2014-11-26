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

import logging
import os

from oslo.config import cfg
import six
import voluptuous
import yaml

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class Credentials(object):

    """Credentials class is in charge of loading the login/password."""

    def __init__(self):
        """Initialize the Credentials object

        Try to load credential in this order:

            - from the credentials_file
            - from the ~/.config/mincer/credentials.yaml file
            - from the OpenStack OS_ environment variables

        :param credentials_file: location of a credential file (optional)

        """
        default_credentials_file = (
            "%s/.config/mincer/credentials.yaml" % os.environ['HOME'])
        if CONF.credentials_file:
            raw = self._get_from_file(CONF.credentials_file)
        elif os.path.exists(default_credentials_file):
            raw = self._get_from_file(default_credentials_file)
        else:
            raw = self._get_from_environ()

        credentials = self._expand_credentials(raw)
        self._validate_credentials(credentials)
        self.credentials = credentials

    def _get_from_file(self, credentials_file):
        """Load credentials from a given file

        :param credentials_file: location of the file
        :type credentials_file: str

        """
        with open(credentials_file, 'rb') as cred_file:
            return yaml.load(cred_file.read())

    def _get_from_environ(self):
        """Load credentials from the environment variables

        This method return a dictionnary initialized to load the variable
        from the environment. Variable content will be expanded by
        _expand_credentials.

        :returns: the environment
        :rtype: dict

        """
        return {'os_auth_url': '$OS_AUTH_URL',
                'os_username': '$OS_USERNAME',
                'os_password': '$OS_PASSWORD',
                'os_tenant_name': '$OS_TENANT_NAME'}

    def _expand_credentials(self, raw_credentials):
        """return the credentials for the provider.

        variable `$foo` are expanded with environment variable called `foo`.

        :param raw_credentials: the credentials dict
        :type raw_credentials: dict
        :returns: the credentials
        :rtype: dict

        """
        credentials = {}
        for credential, value in six.iteritems(raw_credentials):
            if value.startswith("$"):
                credentials[credential] = os.environ.get(value[1:])
                if credentials[credential] is None:
                    raise ValueError("Env variable '%s' not set" % value)
            else:
                credentials[credential] = value
        return credentials

    def _validate_credentials(self, credentials):
        """Validate the credentials with voluptuous

        Raise a voluptuous.MultipleInvalid exception in case of
        error.

        :param credentials: the credentials
        :type credentials: dict

        """
        Required = voluptuous.Required

        schema = voluptuous.Schema({
            Required('os_auth_url'): str,
            Required('os_username'): str,
            Required('os_password'): str,
            Required('os_tenant_name'): str})
        try:
            schema(credentials)
        except voluptuous.MultipleInvalid as e:
            LOG.error("Invalide credentials: %s" % e)
            raise e

    def get(self):
        """Return the credentials

        :returns: the credentials
        :rtype: dict
        """
        return self.credentials
