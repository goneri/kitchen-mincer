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

from mincer import action
from mincer import media  # noqa

LOG = logging.getLogger(__name__)


class RunCommand(action.PluginActionBase):

    """Action to run a script on a given machine.

    If the hosts key is not defined, the command is called from the
    gateway machine.

    """

    def launch(self, marmite):
        """Call the action

        :returns: None
        :rtype: None

        """
        hosts = self.args.get('hosts', [None])
        for host in hosts:
            for command in self.args['commands']:
                self.provider.run(command, host=host)
