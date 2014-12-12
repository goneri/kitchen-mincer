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


class UpdateInfra(action.PluginActionBase):

    """Start the application infrastructure."""

    def launch(self):
        """Launch the deployment."""
        LOG.info("Starting deployment..")
        self.provider.create_or_update_stack(
            stack_id=self.provider._application_stack.get_id(),
            template_path=self.args['heat_file'])
        self.provider.wait_for_status_changes(
            self.provider._application_stack.get_id(),
            ['COMPLETE'])