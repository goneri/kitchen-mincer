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

import tempfile
import unittest

import fixtures
import mock
import testtools

import mincer.action
import mincer.actions.background_check as background_check
import mincer.actions.run_command as run_command
import mincer.actions.serverspec_check as serverspec_check
import mincer.actions.simple_check as simple_check
import mincer.actions.start_infra as start_infra
import mincer.actions.update_infra as update_infra
import mincer.actions.upload_images as upload_images
import mincer.providers.heat. provider as provider

action_list = [
    simple_check.SimpleCheck,
    start_infra.StartInfra,
    serverspec_check.Serverspec]


class fake_provider(object):

    def __init__(self):
        self.application_stack_id = "Rambo"
        self.priv_key = "my priv key"

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
        my_action = mincer.action.ActionBase({})
        self.assertRaises(NotImplementedError, my_action.launch, None, None)


class TestStartInfra(testtools.TestCase):
    def test_launch(self):
        provider = mock.Mock()
        provider.pub_key.return_value = "toto"
        marmite = mock.Mock()
        marmite.fs_layer = mock.Mock()
        marmite.fs_layer.get_file.return_value = 'a raw heat template'
        provider.pub_key.return_value = "toto"
        my_action = start_infra.StartInfra({})
        self.assertEqual(my_action.launch(
            marmite=marmite, provider=provider), None)
        provider.register_pub_key.assert_called_with("toto")
        provider.launch_application.assert_called_with(
            'a raw heat template')
        provider.init_ssh_transport.assert_called_with()


class TestUpdateInfra(testtools.TestCase):
    def test_launch(self):
        provider = mock.Mock()
        provider._application_stack.get_id.return_value = "Belette verte"
        provider.pub_key = "toto"
        my_action = update_infra.UpdateInfra(
            {'heat_file': 'foo'})
        self.assertEqual(my_action.launch(
            marmite=None, provider=provider), None)
        provider.create_or_update_stack.assert_called_with(
            stack_id='Belette verte', template_path='foo')
        provider.wait_for_status_changes.assert_called_with(
            'Belette verte', ['COMPLETE'])


class TestServerspec(testtools.TestCase):
    def test_launch(self):
        my_action = serverspec_check.Serverspec({'targets': []})
        self.assertIsInstance(my_action.launch(
            marmite=None, provider=fake_provider()), dict)

    def test__get_targets_ips(self):
        my_action = serverspec_check.Serverspec({
            'targets': {'t1000': 'a', 'hal': 'b'}})
        targets_ips = my_action._get_targets_ips(fake_provider())
        self.assertEqual(targets_ips, {'target': '2.3.4.5'})


class TestSimpleCheck(testtools.TestCase):

    def test_simple_check(self):
        my_provider = mock.Mock()
        my_action = simple_check.SimpleCheck(
            {'hosts': ['my_instance'], 'commands': ['uname']})
        self.assertEqual(my_action.launch(
            marmite=None, provider=my_provider), None)
        my_provider.run.assert_called_once_with('uname')


class TestRunCommand(testtools.TestCase):

    def test_run_command(self):
        my_action = run_command.RunCommand(
            {'hosts': ['my_instance'], 'commands': ['uname']})
        provider = mock.Mock()
        self.assertEqual(my_action.launch(
            marmite=None, provider=provider),
                         None)
        provider.run.assert_called_with('uname', host='my_instance')

    def test_run_command_with_no_hosts(self):
        my_action = run_command.RunCommand(
            {'commands': ['uname']})
        self.assertEqual(my_action.launch(
            marmite=None, provider=fake_provider()), None)


class TestUploadImages(testtools.TestCase):
    def setUp(self):
        super(TestUploadImages, self).setUp()
        self.useFixture(fixtures.NestedTempfile())

    @mock.patch('mincer.actions.upload_images.upload_images.CONF')
    def test_upload_images(self, CONF):
        CONF.refresh_medias = {}
        my_provider = mock.Mock()
        tf = tempfile.NamedTemporaryFile()
        my_action = upload_images.UploadImages(
            {'medias':
                {'img1':
                    {'type': 'local',
                     'disk_format': 'qcow2',
                     'path': tf.name}}})
        self.assertEqual(my_action.launch(
            marmite=None, provider=my_provider), None)
        self.assertTrue(my_provider.upload.called)


class TestBackgroundCheck(testtools.TestCase):

    def test_background_check(self):
        provider = mock.Mock()
        my_action = background_check.BackgroundCheck(
            {'params': ['echo a']})
        my_action.launch(marmite=None, provider=provider)
        provider.register_check.assert_called_with('echo a')

if __name__ == '__main__':
    unittest.main()
