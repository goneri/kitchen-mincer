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

import mock
import testtools

import mincer.action
import mincer.actions.local_script as local_script
import mincer.actions.run_command as run_command
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

    def init_ssh_transport(self):
        pass

    def run(self, command, host=None):
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
        self.assertEqual(my_action.launch(), None)


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


class TestSimpleCheck(testtools.TestCase):

    def test_simple_check(self):
        my_action = simple_check.SimpleCheck(
            {'hosts': ['my_instance'], 'commands': ['uname']},
            fake_provider(),
            None)
        self.assertEqual(my_action.launch(), None)


class TestRunCommand(testtools.TestCase):

    def test_run_command(self):
        my_action = run_command.RunCommand(
            {'hosts': ['my_instance'], 'commands': ['uname']},
            fake_provider(),
            None)
        self.assertEqual(my_action.launch(), None)

if __name__ == '__main__':
    unittest.main()
