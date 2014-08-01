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

LOG = logging.getLogger(__name__)


class Directory(object):
    """Store log in a local directory.

    The YAML configuration structure is:

    .. code-block:: yaml

        -
            name: local
            driver: directory
            path: /tmp
            suffix: .my_log

    * name: a name used to identify the dispatcher.
    * driver: must by directory to use this module.
    * path: a directory on the filesystem. The default is the local directory.
    * suffix: the suffix of the file name of the log file (default: .log)
    """

    def __init__(self, params, provider):
        self.params = params

        self._path = params.get('path', '.')
        self._suffix = params.get('suffix', '.log')

    def store(self, name, content):
        """Save a log content in a file on the local file system.

        Keyword arguments:
        name -- the name of the file
        content -- a StringIO instance
        """
        fp = os.path.join(self._path, name + self._suffix)
        with open(fp, 'w') as f:
            for line in content.getvalue():
                f.write(line)
