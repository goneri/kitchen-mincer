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


class Serverspec(object):
    """Deploy Serverspec stack and run rake command.

    The Serverspec driver deploy a stack which run the rake command
    from within the stack.
    """

    def __init__(self, refresh_medias, provider, params, medias, private_key):
        """:param refresh_medias: the medias to reupload
           :type group_id: list
           :param provider: the provider to use
           :type provider: mincer.providers.heat.provider.Heat
           :param params: the parameters needed by serverspec
           :type params: list
           :param medias: list of Media objects associated to the driver
           :type medias: list
           :parma private_key: the private key to use
           :type private_key: str
        """

        self._refresh_medias = refresh_medias
        self._provider = provider
        self._params = params
        self._test_medias = medias
        self._private_key = private_key

    def _get_server_spec_template_path(self):
        """Returns the path of the serverspec Heat template."""

        module_abs_path = os.path.abspath(__file__)
        module_dir_abs_path = os.path.dirname(module_abs_path)
        return "%s/static/serverspec.yaml" % module_dir_abs_path

    def _get_targets_ips(self):
        """Returns the ip address associated of the targets."""

        targets_ips = {}
        targets = self._params()["targets"]
        for machine in self._provider.get_machines():
            for target in targets:
                if target in machine["name"]:
                    targets_ips["target"] = machine["primary_ip_address"]
        return targets_ips

    def launch(self):
        """Launch the Serverspec test."""

        LOG.info("Run Serverspec tests...")

        parameters = {"test_private_key": self._private_key}
        parameters.update(self._get_targets_ips())

        volumes = self._provider.upload(self._test_medias(),
                                        self._refresh_medias)
        parameters.update(volumes)

        LOG.debug("parameters: %s" % str(parameters))

        LOG.info("Running Serverspec stack test")
        tmp_stack_id = self._provider.create_stack(
            'serverspec%s' % self._provider.application_stack_id,
            self._get_server_spec_template_path(),
            parameters
        )

        self._provider.delete_stack(tmp_stack_id)
