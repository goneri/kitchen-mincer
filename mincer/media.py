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

"""Retrieve and upload data."""

import hashlib
import logging
import os
import subprocess
import tarfile
import tempfile

LOG = logging.getLogger(__name__)

try:
    import guestfs
except ImportError:
    LOG.error("python-guestfs package is required to procude “dynamic” image")
    guestfs = None


class MediaManagerException(Exception):
    """Base class for media manager exceptions.
    """


class Media(object):

    def __init__(self, name, description):
        self.disk_format = "raw"
        self._min_image_size = 1024 * 1024 * 10
        self.name = name
        self._type = description.get('type')
        self.checksum = description.get('checksum')
        self.disk_format = description.get('disk_format', 'raw')
        self._local_image = None
        self.copy_from = description.get('copy_from')
        self.checksum = description.get('checksum')

        # TODO(Gonéri): move this in a subclass/driver
        if self._type == "dynamic":
            self.basedir = tempfile.mkdtemp()
            self._sources = description['sources']
            self.data_dir = "%s/data" % self.basedir
            self._dynamic_image = "%s/disk.img" % self.basedir
            os.makedirs(self.data_dir)
        elif self._type == "local":
            try:
                self._local_image = description['path']
            except KeyError:
                raise MediaManagerException("Missing key 'path''")

    def generate(self):
        """Publish method to generate an image."""
        if self._type == "dynamic":
            self._collect_data()
            self._produce_image()

    def getPath(self):
        """Returns the path to the disk image."""
        if self._type == "dynamic":
            return self._dynamic_image
        elif self._type == "local":
            return self._local_image

    def _collect_data(self):
        """Retrieve the ressources from different localisation and
        store them in a work directory

        ressources is a mandatory parameter.
        """
        for source in self._sources:

            target_dir = "%s/%s" % (self.data_dir, source['target'])
            os.makedirs(target_dir)

            if source['type'] == 'git':
                subprocess.call(["git", "clone", "--depth", "1",
                                 source['value'], target_dir],
                                cwd=self.data_dir)
            elif source['type'] == 'script':
                os.environ['BASE_DIR'] = os.getcwd()
                f = tempfile.NamedTemporaryFile(delete=False)
                f.write(source['value'])
                f.close()
                subprocess.call(["chmod", "+x", f.name])
                subprocess.call([f.name], cwd=target_dir)
                os.unlink(f.name)
            else:
                raise MediaManagerException("Unknown source type '%s'" %
                                            source['type'])

    def _size_to_allocate(self, tarfile_path):
        """Return the size to allocate for the image."""
        # The final size consists of the size of the tar file and
        # the size of the metadatas of the FS which is majored to 15 percent.
        # For the same reason, we ensure size is greater than
        # self._min_image_size.
        disk_image_size = os.path.getsize(tarfile_path) * 1.15
        if disk_image_size < self._min_image_size:
            disk_image_size = self._min_image_size

        return disk_image_size

    def _produce_image(self):
        """Push the collected data in an image
        """
        tarfile_path = "%s/final.tar" % self.basedir
        with tarfile.open(tarfile_path, "w") as tar:
            tar.add(self.data_dir, arcname=os.path.basename(self.data_dir))

        disk_image_size = self._size_to_allocate(tarfile_path)
        g = None
        try:
            with open(self._dynamic_image, "w") as f:
                f.truncate(disk_image_size)

            g = guestfs.GuestFS()
            g.add_drive_opts(self._dynamic_image, format="raw", readonly=0)
            g.launch()
            devices = g.list_devices()
            assert len(devices) == 1
            g.part_disk(devices[0], "mbr")
            partitions = g.list_partitions()
            g.mkfs("ext2", partitions[0])
            g.mount(partitions[0], "/")
            g.tar_in(tarfile_path, '/')
            os.unlink(tarfile_path)
        finally:
            if g:
                g.close()
        self.checksum = hashlib.md5(self._dynamic_image).hexdigest()
