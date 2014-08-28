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

LOG = logging.getLogger(__name__)


class PyLogger(object):

    """Push the log in the internal logger

    The YAML configuration structure is:

    .. code-block:: yaml

        -
            name: Python internal logger
            driver: logging

    * name: a name used to identify the dispatcher.
    * driver: must by directory to use this module.
    """

    def __init__(self, params, provider=None):
        """constructor of logging logdispatcher driver.

        :param params: the logdispatcher parameter structure
        :type params: dict
        :param provider: the provider (unused)
        :type provider: a provider instance

        """
        self.params = params

    def store(self, name, content):
        """Print the log content in a file on the local file system.

        Keyword arguments:
        :param name: the name of the file
        :type name: str
        :param content: the log content
        :type content: a StringIO instance

        """
        LOG.info("output of `%s'" % name)
        LOG.info(content.getvalue())
