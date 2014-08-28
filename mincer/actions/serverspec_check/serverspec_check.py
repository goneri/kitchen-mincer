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

from mincer import action

LOG = logging.getLogger(__name__)


class Serverspec(action.PluginActionBase):
    """Deploy Serverspec stack and run rake command.

    The Serverspec driver deploy a stack which run the rake command
    from within the stack.
    """
    def _get_server_spec_template_path(self):
        """Returns the path of the serverspec Heat template."""

        module_abs_path = os.path.abspath(__file__)
        module_dir_abs_path = os.path.dirname(module_abs_path)
        return "%s/static/serverspec.yaml" % module_dir_abs_path

    def _get_targets_ips(self):
        """Returns the ip address associated of the targets."""

        targets_ips = {}
        targets = self.args["targets"]
        for machine in self.provider.get_machines():
            for target in targets:
                if target in machine["resource_name"]:
                    targets_ips["target"] = machine["primary_ip_address"]
        return targets_ips

    def launch(self):
        """Launch the Serverspec test."""

        LOG.info("Run Serverspec tests...")

        parameters = {"test_private_key": self._private_key}
        parameters.update(self._get_targets_ips())

        LOG.debug("parameters: %s" % str(parameters))

        LOG.info("Running Serverspec stack test")
        tmp_stack = self.provider.create_stack(
            'serverspec%s' % self.provider.application_stack_id,
            self._get_server_spec_template_path(),
            parameters
        )

        self.provider.delete_stack(tmp_stack.get_id())
        return tmp_stack.get_logs()
