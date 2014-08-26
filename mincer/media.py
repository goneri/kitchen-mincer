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


class MediaManagerException(Exception):

    """Base class for media manager exceptions."""


class Media(object):

    """Media associated with the application.

    A media section is a hash of hash table structure.

    .. code-block:: yaml

        medias:
            my_first_media_name:
            # media definition
            my_second_media_name:
            # media definition

     A media entry has a **type** key and some associated additional keys.

     * type **dynamic**: The image is generated on the mincer machine from
       a serie of directives (*sources*).
     * Type **local**: The image already exists on the machine. The *path*
       key is used to specify the image location.
     * Type **block**: The image already exists on a remote HTTP server.


    The YAML configuration structure for a dynamic media:

    .. code-block:: yaml
        :linenos:

        medias:
          dump_mysql:
            type: dynamic
            sources:
              -
                driver: script
                value: |
                    #!/bin/sh
                    cp $BASE_DIR/samples/wordpress/backup_wordpress.sql .
                target: mysql
              -
                driver: git
                value: https://github.com/WordPress/WordPress
                target: wordpress
                ref: 3.8.2

    * medias: the root key of the media hash table.
    * dump_mysql: the name of the media.
    * type: the type of media, here dynamic
    * sources: the component used to generate the dynamic media
        * script:
            * value: the script to call
            * target: where to store the content
        * git
            * value: the Git repository URL
            * target: where to store the content
            * ref: the Git reference to pull. The default is *master*

    YAML of a bloc media:

    .. code-block:: yaml
        :linenos:

        medias:
            ubuntu-13.10-server-amd64.iso:
                type: block
                disk_format: iso
                copy_from: http://my.mirror/ubuntu-13.10-server-amd64.iso
                checksum: 4d1a8b720cdd14b76ed9410c63a00d0e
            base_image:
                type: block
                disk_format: qcow2
                copy_from: http://my.mirror/ubuntu-vm.qcow2
                checksum: e3224ba9d93b1df12db3b9e1d2f34ea7

    The following keys can be used:

        * disk_format: default is qcow2
        * copy_from: the HTTP URL to the image
        * checksum: the checksum of the image

    """

    def __init__(self, name, description):
        """Media object constructor

        :param name: the name of the media
        :type name: str
        :param description: the description of the object
        :type description: dict
        :returns: None
        :rtype: None

        """
        self.disk_format = "raw"
        self._min_image_size = (1024 * 1024 * 10)
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
        """Return the path to the disk image."""
        if self._type == "dynamic":
            return self._dynamic_image
        elif self._type == "local":
            return self._local_image

    def _collect_data(self):
        """Process the different sources

        Retrieve the ressources from different localisation and
        store them in a work directory
        """
        for source in self._sources:

            target_dir = "%s/%s" % (self.data_dir, source['target'])
            os.makedirs(target_dir)
            LOG.debug("target_dir: '%s'" % target_dir)

            if source['driver'] == 'git':
                subprocess.call(["git", "clone", "--depth", "1",
                                 source['value'], target_dir],
                                cwd=self.data_dir)
            elif source['driver'] == 'local':
                subprocess.call("cp -r %s/* %s" % (source['path'], target_dir),
                                shell=True)
            elif source['driver'] == 'script':
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
        """Push the collected data in an image."""
        try:
            import guestfs
        except ImportError:
            LOG.error("python-guestfs package is required to "
                      "produce 'dynamic' image")
            guestfs = None

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
        self.checksum = hashlib.md5(
            self._dynamic_image.encode(encoding='ASCII')).hexdigest()
