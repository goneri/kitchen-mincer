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
import yaml

from mincer import media  # noqa

LOG = logging.getLogger(__name__)


class HeatConfig(object):
    def __init__(self):
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
        self.struct['outputs']['stdout_%i_d' % self._test_cpt] = {
            'value': {
                'get_attr': ['%i_d' % self._test_cpt, 'deploy_stdout']
            }
        }

    def get_yaml(self):
        return yaml.dump(self.struct)


class SimpleCheck(object):

    def __init__(self, refresh_medias, provider, params, medias):
        self._refresh_medias = refresh_medias
        self.provider = provider
        self.params = params
        self.medias = medias

    def _save_test_results(self, result, error_code):
        with open("/tmp/test_results", "wb") as file_result:
            file_result.write(result)
            if error_code == 0:
                file_result.write("\n ===> Test success ! \o/\n\n")
            else:
                file_result.write("\n ===> Test failed !\n")

    def _feed_stack(self, cmd, machine_ip, heat_config):
        command = string.Template(cmd).substitute({"IP": machine_ip})
        heat_config.add_test(command)

    def launch(self):

        heat_config = HeatConfig()

        params = self.params()
        for machine in self.provider.get_machines():
            for target in params:
                if target == '_ALL_' or target == machine["name"]:
                    machine_ip = machine["primary_ip_address"]
                    cmd = params[target]
                    self._feed_stack(cmd, machine_ip, heat_config)
                else:
                    raise TargetNotFound("target '%s' not found" % target)

        medias = self.medias()
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(heat_config.get_yaml())
        fname = f.name
        f.close()
        tmp_stack_id = self.provider.create_stack(
            'simple-test-stack' + self.provider.application_stack_id,
            fname,
            self.provider.upload(medias, self._refresh_medias)
        )
        os.unlink(fname)
        self.provider.delete_stack(tmp_stack_id)


class TargetNotFound(Exception):
    """Exception raised when an object is not found."""
