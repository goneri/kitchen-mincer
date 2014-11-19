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

LOG = logging.getLogger(__name__)


class StartInfra(action.PluginActionBase):

    """Start the application infrastructure."""

    def launch(self, marmite):
        """Launch the deployment."""
        LOG.info("Starting deployment..")
        self.provider.register_pub_key(self.provider.pub_key())
        heat_file = self.args.get('heat_file', 'heat.yaml')
        self.provider.launch_application(
            marmite.fs_layer.get_file(heat_file))
        self.provider.init_ssh_transport()
