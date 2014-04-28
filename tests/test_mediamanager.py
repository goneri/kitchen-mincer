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

import fixtures
import mock
import os
import tempfile
import testtools
import unittest

try:
    import guestfs
    from mincer import mediamanager  # noqa
except ImportError:
    guestfs = None

SAMPLE_MEDIAS = [
    {
        'type': 'git',
        'uri': 'git://example.com/repo.git',
        'target': 'result_git',
    },
    {
        'type': 'script',
        'target': 'result_script',
        'content': '''
#!/bin/sh
touch Roberto
'''
    },
]


def _add_some_files(directory):
    subdirs = ['/foo', '/foo/bar']

    for subdir in subdirs:
        os.mkdir(directory + subdir)
        f = open(directory + subdir + '/file', 'w')
        f.write("foobar" * 10000)
        f.close()


class TestMediaManager(testtools.TestCase):

    @testtools.skipUnless(
        guestfs,
        "Use this test only when we have guestfs installed")
    def setUp(self):
        super(TestMediaManager, self).setUp()

        self.useFixture(fixtures.NestedTempfile())
        self.mm = mediamanager.MediaManager()
        self.assertIsInstance(self.mm, mediamanager.MediaManager)

        self.tdir_empty = tempfile.mkdtemp()
        self.tdir_with_data = tempfile.mkdtemp()

        _add_some_files(self.tdir_with_data)

    def test_get_data_size(self):
        self.assertEqual(self.mm.get_data_size(self.tdir_empty), 0)
        self.assertEqual(self.mm.get_data_size(self.tdir_with_data), 120000)

    def test_produce_image(self):
        mm = mediamanager.MediaManager()

        _add_some_files(mm.data_dir)

        with mock.patch('tarfile.open') as MockClass:
            MockClass.return_value = False
            self.assertRaises(mediamanager.MediaManagerException,
                              mm.produce_image)

        with mock.patch("guestfs.GuestFS") as Mock:
            Mock.return_value = False
            self.assertRaises(mediamanager.MediaManagerException,
                              mm.produce_image)

    def test_collect_data(self):
        with mock.patch('subprocess.call') as MockClass:
            MockClass.return_value = True
            self.mm.collect_data(ressources=SAMPLE_MEDIAS)


if __name__ == '__main__':
    unittest.main()
