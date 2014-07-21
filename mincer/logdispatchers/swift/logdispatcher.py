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
import string

import swiftclient

LOG = logging.getLogger(__name__)


class Swift(object):
    """Store log in a local directory.

    The YAML configuration structure is:

    .. code-block:: yaml

        -
            name: os-ci-test6
            driver: swift
            container: log
            path_template: somewhere/$name
        -
            name: os-ci-test7
            driver: swift
            container: log
            identity:
                user: admin
                key: password
                authurl: http://os-ci-test7.ring.enovance.com:5000/v2.0
                tenant_name: demo


    * name: a name used to identify the dispatcher.
    * driver: must by directory to use this module.
    * path_template: a directory on the filesystem. The default is `log/$name`.
      The `$name` variable will be expended with the name of the file.
    * suffix: the suffix of the file name of the log file (default: .log)

    **Server authentification**: the default is to try to access the Swift
    of the **provider**. If you need to access another another Heat server,
    you can add an `identity` section with the following keys:

    * user: the username
    * key: the password of the account
    * authurl: the API URL of the OpenStack, e.g:
      `http://os-ci-test7.ring.enovance.com:5000/v2.0`
    * tenant_name: the name of the OpenStack tenant (project)
    """

    def __init__(self, params, provider):
        self.params = params

        self._container = params.get('container', 'log')
        self._path_template = params.get('path_template', 'log/$name')
        if 'identity' in params:
            self._swift_handler = swiftclient.client.Connection(
                user=params['identity']['user'],
                key=params['identity']['key'],
                authurl=params['identity']['authurl'],
                tenant_name=params['identity']['tenant_name'],
                auth_version='2.0')
        else:
            self._swift_handler = provider.swift

        try:
            self._swift_handler.head_container(self._container)
        except swiftclient.exceptions.ClientException as e:
            LOG.error("Fail to access Swift container '%s'" % self._container)
            raise e

    def _get_full_path(self, name=''):
        file_path_template = string.Template(self._path_template)
        return file_path_template.substitute(name=name)

    def store(self, name, content):
        """Save a log content in a file on the local file system.

        Keyword arguments:
        name -- the name of the file
        content -- a StringIO instance
        """
        self._swift_handler.put_object(
            self._container,
            self._get_full_path(name),
            content.getvalue()
        )
