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
import string
import tempfile
import uuid

import yaml

from mincer import action
from mincer import media  # noqa

LOG = logging.getLogger(__name__)


class HeatConfig(object):

    """Heat config for the SimpleCheck action."""

    def __init__(self):
        """Constructor for HeatConfig object."""
        self.struct = {
            'heat_template_version': '2013-05-23',
            'description': 'Zoubida',
            'parameters': {
                'volume_id_base_image': {
                    'type': 'string',
                    'description': 'The VM root system'
                }
            },
            'resources': {
                'tester_instance': {
                    'type': 'OS::Nova::Server',
                    'properties': {
                        'image': {'get_param': 'volume_id_base_image'},
                        'user_data_format': 'SOFTWARE_CONFIG',
                        'flavor': 'm1.small'
                    }
                }
            },
            'outputs': {}
        }

        # TODO(Gonéri)
        self.struct['resources']['tester_instance']['properties']['image'] = \
            {'get_param': 'volume_id_base_image'}
        self._test_cpt = 0

    def add_test(self, cmd):
        """Store a command in the Heat template

        Put a command in the heat template as a SoftwareConfig script

        :param cmd: the command to call
        :type cmd: str
        :returns: None
        :rtype: None

        """
        self.struct['resources']['%i_c' % self._test_cpt] = {
            'type': 'OS::Heat::SoftwareConfig',
            'properties': {
                'group': 'script',
                # TODO(Gonéri): str() otherwise we generate
                # an unicode string rejected by Heat (py27)
                'config': str('#!/bin/sh\n%s\n' % cmd)
            }
        }
        self.struct['resources']['%i_d' % self._test_cpt] = {
            'type': 'OS::Heat::SoftwareDeployment',
            'properties': {
                'config': {
                    'get_resource': '%i_c' % self._test_cpt
                },
                'server': {
                    'get_resource': 'tester_instance'
                }
            }
        }
        self.struct['outputs']['simple_test_%i' % self._test_cpt] = {
            'description': str(cmd),
            'value': {
                'get_attr': ['%i_d' % self._test_cpt, 'deploy_stdout']
            }
        }
        self._test_cpt += 1

    def get_yaml(self):
        """Return the Heat template

        :returns: the Heat template as a YAML string
        :rtype: str

        """
        return yaml.dump(self.struct)


class SimpleCheck(action.PluginActionBase):

    """An action designed to validate an application with simple command."""

    def _prepare_check_commands(self, machines, params):
        """Add the list of check commands to run

        :param machines: the machines found in the application stack
        :type machines: list of dict()
        :param params: the structure used to configure the action
        :type params: dict

        """
        cmds = []
        for machine in machines:
            for target in params:
                if target == '_ALL_' or target == machine["name"]:
                    machine_ip = machine["primary_ip_address"]
                    cmd_tpl = params[target]
                    cmd = string.Template(cmd_tpl).substitute(
                        {"IP": machine_ip})
                    cmds.append(cmd)
        return sorted(cmds)

    def _get_temp_stack_file(self, heat_config):
        """Return the heat_config as a temporary file

        .. note:: The temporary file has to been removed.

        :param heat_config: a HeatConfig instance

        """
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(bytearray(heat_config.get_yaml(), 'UTF-8'))
        fname = f.name
        f.close()
        return fname

    def launch(self):
        """Call the action."""
        heat_config = HeatConfig()

        for cmd in self._prepare_check_commands(
                self.provider.get_machines(),
                self.params):
            heat_config.add_test(cmd)

        # TODO(Gonéri): Probably not needed anymore
        medias = self.medias

        fname = self._get_temp_stack_file(heat_config)
        tmp_stack = self.provider.create_stack(
            'simple-test-%s' % uuid.uuid1(),
            fname,
            medias
        )
        os.unlink(fname)
        self.provider.delete_stack(tmp_stack.get_id())
        return tmp_stack.get_logs()


class TargetNotFound(Exception):

    """Exception raised when an object is not found."""
