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

import mincer.utils.fs_layer

import fixtures
import testtools


class TestFSLayer(testtools.TestCase):
    def setUp(self):
        super(TestFSLayer, self).setUp()
        self.useFixture(fixtures.NestedTempfile())
        self.tmp_dir = tempfile.mkdtemp()
        fd = open(self.tmp_dir + '/file', 'w')
        fd.write('George Abitbol')
        fd = open(self.tmp_dir + '/file_with_tpl', 'w')
        fd.write('George Abitbol: {{ bob }}')
        fd = open(self.tmp_dir + '/file_with_yaml', 'w')
        fd.write('George Abitbol: Ah, voila enfin le roi de la classe !')
        self.my_local_fs_layer = mincer.utils.fs_layer.FSLayer(
            self.tmp_dir)
        self.my_remote_fs_layer = mincer.utils.fs_layer.FSLayer(
            'http://example/somewhere')

    def test_remote(self):
        self.assertFalse(self.my_local_fs_layer.remote)
        self.assertTrue(self.my_remote_fs_layer.remote)

    def test_get_file(self):
        self.assertEqual(
            self.my_local_fs_layer.get_file('file'),
            'George Abitbol')

    def test_get_file_template(self):
        self.assertEqual(
            self.my_local_fs_layer.get_file(
                'file_with_tpl',
                template_values={
                    'bob': 'Ah, voila enfin le roi de la classe !'}),
            'George Abitbol: Ah, voila enfin le roi de la classe !')

    def test_get_file_yaml(self):
        self.assertEqual(
            self.my_local_fs_layer.get_file(
                'file_with_yaml',
                load_yaml=True),
            {'George Abitbol': 'Ah, voila enfin le roi de la classe !'})
