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

import functools
import hashlib
import os
import subprocess
import tarfile
import tempfile

import guestfs


class MediaManagerException(Exception):
    """Base class for media manager exceptions.
    """


class Media(object):

    def __init__(self, name, description):
        self.disk_format = "raw"
        self.name = name
        self._type = description.get('type')
        self._disk_image_file = None
        self.checksum = description.get('checksum')
        self.disk_format = description.get('disk_format', 'raw')
        self.location = description.get('location')
        self.copy_from = description.get('copy_from')
        self.checksum = description.get('checksum')

        # TODO(Gonéri): move this in a subclass/driver
        if self._type == "dynamic":
            self.basedir = tempfile.mkdtemp()
            self._sources = description['sources']
            self.data_dir = "%s/data" % self.basedir
            self._disk_image_file = "%s/disk.img" % self.basedir
            os.makedirs(self.data_dir)

    def generate(self):
        """Publish method to generate an image."""
        if self._type == "dynamic":
            self._collect_data()
            self._produce_image()

    def getPath(self):
        """Returns the path to the temporary disk image."""
        return self._disk_image_file

    def _get_data_size(self, p):
        """Compute the size, in bytes of a directory
        """
        prepend = functools.partial(os.path.join, p)
        return sum([(os.path.getsize(f) if os.path.isfile(f) else
                   self._get_data_size(f))
                   for f in map(prepend, os.listdir(p))])

    def _collect_data(self):
        """Retrieve the ressources from different location and
        store them in a work directory

        ressources is a mandatory parameter.
        """
        for source in self._sources:

            target_dir = "%s/%s" % (self.data_dir, source['target'])
            os.makedirs(target_dir)

            if source['type'] == 'git':
                subprocess.call(["git", "clone", source['value'], target_dir],
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

    def _produce_image(self):
        """Push the collected data in an image
        """
        size = self._get_data_size(self.data_dir) + 50 * 1024 * 1024

        tarfile_name = "%s/final.tar" % self.basedir
        try:
            with tarfile.open(tarfile_name, "w") as tar:
                tar.add(self.data_dir, arcname=os.path.basename(self.data_dir))
        except Exception:
            raise MediaManagerException("Failed to move content in '%s'"
                                        % tarfile_name)
        try:
            with open(self._disk_image_file, "w") as f:
                f.truncate(size)
                f.close()

            g = guestfs.GuestFS()
            g.add_drive_opts(self._disk_image_file, format="raw", readonly=0)
            g.launch()
            devices = g.list_devices()
            assert len(devices) == 1
            g.part_disk(devices[0], "mbr")
            partitions = g.list_partitions()
            g.mkfs("ext2", partitions[0])
            g.mount(partitions[0], "/")
            g.tar_in(tarfile_name, '/')
            os.unlink(tarfile_name)
        except Exception:
            raise MediaManagerException("Failed to move data in the image '%s'"
                                        % self._disk_image_file)
        finally:
            if g:
                g.close()
        self.checksum = hashlib.md5(self._disk_image_file).hexdigest()
