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
            {'name': 'hal', 'primary_ip_address': '1.2.3.4'},
            {'name': 't1000', 'primary_ip_address': '2.3.4.5'}])

    def create_stack(self, a, b, c):
        return({'stack_id': 'George'})

    def delete_stack(self, a):
        pass

    def launch_application(self):
        pass

    def upload(self, a):
        pass

    def retrieve_log(self, a):
        pass


class TestBase(testtools.TestCase):
    def test_init(self):
        """Ensure we preserve the empty list of medias."""
        t = []
        for action in action_list:
            r = action([], fake_provider(), [], [], None)
            t.extend(r.medias)
        self.assertEqual(t, [])

    def test_base(self):
        my_action = mincer.action.PluginActionBase([],
                                     None,
                                     {},
                                     [],
                                     None)
        self.assertRaises(NotImplementedError, my_action.launch)


class TestLocalScript(testtools.TestCase):
    @mock.patch('subprocess.call', mock.Mock(return_value=True))
    def test_launch(self):
        my_action = local_script.LocalScript([],
                                     None,
                                     {'command': 'toto', 'work_dir': '/tmp'},
                                     [],
                                     None)
        self.assertTrue(my_action.launch())


class TestSimpleCheck(testtools.TestCase):

    def setUp(self):
        super(TestSimpleCheck, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    def test_launch(self):
        my_action = simple_check.SimpleCheck([],
                                     fake_provider(),
                                     {'t1000': 'ping', 'hal': 'httping'},
                                     [],
                                     None)
        self.assertEqual(my_action.launch(), None)

    def test__prepare_stack_params(self):
        my_action = simple_check.SimpleCheck([],
                                     fake_provider(),
                                     {},
                                     [],
                                     None)
        sp = my_action._prepare_check_commands(
            [{'name': 'hal', 'primary_ip_address': '1.2.3.4'},
             {'name': 'roy', 'primary_ip_address': '1.2.3.5'},
             {'name': 'uranus', 'primary_ip_address': '1.2.3.6'}],
            {'hal': 'httping $IP', '_ALL_': 'ping -c 5 $IP'})
        self.assertEqual(sp, ['httping 1.2.3.4',
                              'ping -c 5 1.2.3.4',
                              'ping -c 5 1.2.3.5',
                              'ping -c 5 1.2.3.6'])

    def test__get_temp_stack_file(self):
        my_action = simple_check.SimpleCheck([], None, {}, [], None)
        heat_config = simple_check.HeatConfig()
        fname = my_action._get_temp_stack_file(heat_config)
        data = yaml.load(open(fname, 'r'))
        self.assertTrue(data['description'])


class TestStartInfra(testtools.TestCase):
    def test_launch(self):
        my_action = start_infra.StartInfra([],
                                      fake_provider(),
                                      {},
                                      [],
                                      None)
        self.assertEqual(my_action.launch(), None)


class TestServerspec(testtools.TestCase):
    def test_launch(self):
        my_action = serverspec_check.Serverspec([],
                                    fake_provider(),
                                    {'targets': []},
                                    [],
                                    None)
        self.assertEqual(my_action.launch(), None)

    def test__get_targets_ips(self):
        my_action = serverspec_check.Serverspec([],
                                    fake_provider(),
                                    {'targets': {'t1000': 'a', 'hal': 'b'}},
                                    [],
                                    None)
        targets_ips = my_action._get_targets_ips()
        self.assertEqual(targets_ips, {'target': '2.3.4.5'})


if __name__ == '__main__':
    unittest.main()
