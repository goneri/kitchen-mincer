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
import os
import shutil
import subprocess
import tarfile
import tempfile

import guestfs

import glanceclient
import keystoneclient.v2_0


class MediaManagerException(Exception):
    """Base class for media manager exceptions.
    """


class MediaManager(object):

    def __init__(self):

        self.basedir = tempfile.mkdtemp()

        self.data_dir = "%s/data" % self.basedir
        self.disk_image_file = "%s/disk.img" % self.basedir
        os.makedirs(self.data_dir)

    def cleanup(self):

        shutil.rmtree(self.basedir)

    def get_data_size(self, p):
        """Compute the size, in bytes of a directory
        """
        prepend = functools.partial(os.path.join, p)
        return sum([(os.path.getsize(f) if os.path.isfile(f) else
                   self.get_data_size(f)) for f in map(prepend,
                                                       os.listdir(p))])

    def collect_data(self, ressources):
        """Retrieve the ressources from different location and
        store them in a work directory

        ressources is a mandatory parameter.
        """

        for ressource in ressources:

            target_dir = "%s/%s" % (self.data_dir, ressource['target'])
            os.makedirs(target_dir)

            if ressource['type'] == 'git':
                subprocess.call(["git", "clone", ressource['uri'], target_dir],
                                cwd=self.data_dir)

            elif ressource['type'] == 'shell':

                f = tempfile.NamedTemporaryFile()
                f.write(ressource['content'])
                subprocess.call(["chmod", "+x", f.name])
                f.close()
                subprocess.call([f.name], target_dir)

    def produce_image(self):
        """Push the collected data in an image
        """
        size = self.get_data_size(self.data_dir) + 50 * 1024 * 1024

        tarfile_name = "%s/final.tar" % self.basedir
        try:
            with tarfile.open(tarfile_name, "w") as tar:
                tar.add(self.data_dir, arcname=os.path.basename(self.data_dir))
        except Exception:
            raise MediaManagerException("Failed to move content in '%s'"
                                        % tarfile_name)
        try:
            with open(self.disk_image_file, "w") as f:
                f.truncate(size)
                f.close()

            g = guestfs.GuestFS()
            g.add_drive_opts(self.disk_image_file, format="raw", readonly=0)
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
                                        % self.disk_image_file)
        finally:
            if g:
                g.close()

    # TODO(Gonéri) add the ability to use another upload
    # mechanize
    def upload(self, identity=None):
        """Upload an image in Glance
        """
        keystone = keystoneclient.v2_0.Client(
                auth_url=identity['auth_url'],
                username=identity['username'],
                password=identity['password'],
                tenant_name=identity['tenant_name'])
        glance_endpoint = keystone.service_catalog.url_for(
                service_type='image')

        glance = glanceclient.Client(
                2,
                glance_endpoint,
                token=keystone.auth_token)

        image = glance.images.create(
                name="My Test Image",
                disk_format="raw",
                container_format="bare")

        glance.images.upload(image.id, open(self.disk_image_file, 'rb'))
