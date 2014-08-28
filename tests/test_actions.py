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

import unittest

import fixtures
import mock
import testtools
import yaml

import mincer.action
import mincer.actions.local_script as local_script
import mincer.actions.serverspec_check as serverspec_check
import mincer.actions.simple_check as simple_check
import mincer.actions.start_infra as start_infra
import mincer.providers.heat. provider as provider

action_list = [
    local_script.LocalScript,
    simple_check.SimpleCheck,
    start_infra.StartInfra,
    serverspec_check.Serverspec]


class fake_provider(object):

    def __init__(self):
        self.application_stack_id = "Rambo"

    def get_machines(self):
        return([
            {'resource_name': 'hal', 'primary_ip_address': '1.2.3.4'},
            {'resource_name': 't1000', 'primary_ip_address': '2.3.4.5'}])

    def create_stack(self, a, b, c):
        return(provider.Stack('George', {}))

    def delete_stack(self, a):
        pass

    def launch_application(self):
        pass

    def upload(self, a):
        pass

    def retrieve_log(self, a):
        pass


class TestBase(testtools.TestCase):
    def test_base(self):
        my_action = mincer.action.PluginActionBase(
            {},
            None,
            None)
        self.assertRaises(NotImplementedError, my_action.launch)


class TestLocalScript(testtools.TestCase):
    @mock.patch('subprocess.call', mock.Mock(return_value=True))
    def test_launch(self):
        my_action = local_script.LocalScript(
            {'command': 'toto', 'work_dir': '/tmp'},
            None,
            None)
        self.assertTrue(my_action.launch())


class TestSimpleCheck(testtools.TestCase):

    def setUp(self):
        super(TestSimpleCheck, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    def test_launch(self):
        my_action = simple_check.SimpleCheck(
            {'commands': ['httping $t1000 }}']},
            fake_provider(),
            None)
        self.assertEqual(my_action.launch(), {})

    def test__prepare_check_commands(self):
        my_action = simple_check.SimpleCheck(
                                     {},
                                     fake_provider(),
                                     None)
        sp = my_action._prepare_check_commands(
            [{'resource_name': 'hal', 'primary_ip_address': '1.2.3.4'},
             {'resource_name': 'roy', 'primary_ip_address': '1.2.3.5'},
             {'resource_name': 'uranus', 'primary_ip_address': '1.2.3.6'}],
            {'commands': ['httping $hal']})
        self.assertEqual(['httping 1.2.3.4'], sp)

    def test__get_temp_stack_file(self):
        my_action = simple_check.SimpleCheck({}, None, None)
        heat_config = simple_check.HeatConfig()
        heat_config.add_test("echo 33")
        fname = my_action._get_temp_stack_file(heat_config)
        got = yaml.load(open(fname, 'r'))
        expect = {'description': 'Zoubida',
                  'heat_template_version': '2013-05-23',
                  'outputs': {'simple_test_0':
                              {'description': 'echo 33',
                               'value': {'get_attr': ['0_d',
                                                      'deploy_stdout']}}},
                  'parameters': {
                      'volume_id_base_image': {'description':
                                               'The VM root system',
                                               'type': 'string'}},
                  'resources': {'0_c':
                                {'properties': {'config':
                                                '#!/bin/sh\necho 33\n',
                                                'group': 'script'},
                                 'type': 'OS::Heat::SoftwareConfig'},
                                '0_d': {'properties':
                                        {'config': {'get_resource': '0_c'},
                                         'server': {'get_resource':
                                                    'tester_instance'}},
                                        'type':
                                        'OS::Heat::SoftwareDeployment'},
                                'tester_instance': {'properties': {
                                    'flavor': 'm1.small',
                                    'image': {'get_param':
                                              'volume_id_base_image'},
                                    'user_data_format': 'SOFTWARE_CONFIG'},
                                    'type': 'OS::Nova::Server'}}}
        self.assertEqual(got, expect)


class TestStartInfra(testtools.TestCase):
    def test_launch(self):
        my_action = start_infra.StartInfra(
                                      {},
                                      fake_provider(),
                                      None)
        self.assertEqual(my_action.launch(), None)


class TestServerspec(testtools.TestCase):
    def test_launch(self):
        my_action = serverspec_check.Serverspec(
                                    {'targets': []},
                                    fake_provider(),
                                    None)
        self.assertIsInstance(my_action.launch(), dict)

    def test__get_targets_ips(self):
        my_action = serverspec_check.Serverspec(
                                    {'targets': {'t1000': 'a', 'hal': 'b'}},
                                    fake_provider(),
                                    None)
        targets_ips = my_action._get_targets_ips()
        self.assertEqual(targets_ips, {'target': '2.3.4.5'})


if __name__ == '__main__':
    unittest.main()
