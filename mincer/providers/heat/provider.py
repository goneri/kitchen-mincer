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

import glanceclient
import heatclient.client as heatclient
import heatclient.exc as heatclientexc
import keystoneclient.v2_0 as keystone_client


class Heat(object):
    def __init__(self, params={}, args={}):
        self.params = params
        self.args = args
        self._keystone = None

    def connect(self, identity):
        self._keystone = keystone_client.Client(
            auth_url=identity['os_auth_url'],
            username=identity['os_username'],
            password=identity['os_password'],
            tenant_name=identity['os_tenant_name'])

    def _get_heat_template(self):
        with open(self.args.marmite_directory + "/heat.yaml") as file:
            return file.read()

    def upload(self, medias):
        """Upload medias in Glance and returns ids of each medias.

        :param medias: list of Media objects
        :type medias: list
        :returns: list of images's ids
        :rtype: list
        """

        glance_endpoint = self._keystone.service_catalog.url_for(
            service_type='image')

        glance = glanceclient.Client(
            2,
            glance_endpoint,
            token=self._keystone.auth_token)

        # Make an association of checksum and id of existent Glance images.
        checksum_ids_images = {}
        for image in glance.images.list():
            try:
                checksum_ids_images[image.checksum] = image.id
            except AttributeError:
                pass

        # Upload each media if necessary
        images_ids = []
        for media in medias:
            if media.getChecksum() in checksum_ids_images.keys():
                images_ids.append(checksum_ids_images[media.getChecksum()])
                continue

            image = glance.images.create(
                name=media.getName(),
                disk_format="raw",
                container_format="bare")
            with open(media.getPath(), "rb") as media_data:
                glance.images.upload(image.id, media_data)
            images_ids.append(image.id)
        return images_ids

    def create(self):

        heat_endpoint = self._keystone.service_catalog.url_for(
            service_type='orchestration')
        self.heat = heatclient.Client('1', endpoint=heat_endpoint,
                                      token=self._keystone.auth_token)

        hot_template = self._get_heat_template()

        try:
            self.heat.stacks.create(
                stack_name='zoubida',
                parameters={'key_name': 'stack_os-ci-test7'},
                template=hot_template, timeout_mins=60)
        except heatclientexc.HTTPConflict:
            raise AlreadyExisting("Stack '%s' failed because of a conflict"
                                  % 'zoubida')


class AlreadyExisting(Exception):
    """Exception raised when there is a conflict with a stack
    already deployed.
    """


class UploadError(Exception):
    """Exception raised when the mincer failed to upload a media."""
