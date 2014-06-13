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

SAMPLE_MEDIAS = {
    'description': 'Roberto',
    'type': 'dynamic',
    'sources': []
}


def _add_some_files(directory):
    subdirs = ['/foo', '/foo/bar']

    for subdir in subdirs:
        os.mkdir(directory + subdir)
        f = open(directory + subdir + '/file', 'w')
        f.write("foobar" * 10000)
        f.close()


class TestMedia(testtools.TestCase):

    @testtools.skipUnless(
        guestfs,
        "Use this test only when we have guestfs installed")
    def setUp(self):
        super(TestMedia, self).setUp()

        self.useFixture(fixtures.NestedTempfile())
        self.media = mediamanager.Media("Merguez Partie",
                                        {'description': "Yo!",
                                         'type': 'dynamic',
                                         'sources': []})
        self.assertIsInstance(self.media, mediamanager.Media)

        self.tdir_empty = tempfile.mkdtemp()
        self.tdir_with_data = tempfile.mkdtemp()

        _add_some_files(self.tdir_with_data)

    def test_produce_image(self):
        media = mediamanager.Media("Boulghour", SAMPLE_MEDIAS)
        _add_some_files(media.basedir)

        with mock.patch('tarfile.open') as MockClass:
            MockClass.return_value = False
            self.assertRaises(mediamanager.MediaManagerException,
                              media._produce_image)

        with mock.patch("guestfs.GuestFS") as Mock:
            Mock.return_value = False
            self.assertRaises(mediamanager.MediaManagerException,
                              media._produce_image)


if __name__ == '__main__':
    unittest.main()
