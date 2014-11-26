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

import logging

from oslo.config import cfg

from mincer import action
from mincer import media  # noqa

import six

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class UploadImages(action.PluginActionBase):

    """Action to run a script on the local machine."""

    def launch(self):
        """Upload the medias (image)

        :returns: None
        :rtype: None

        """
        medias = {}
        for k, v in six.iteritems(self.args['medias']):
            medias[k] = media.Media(k, v)

        # TODO(Gonéri): replace this provider.medias attribue with a
        # method, e.g: provider.set_media()
        self.provider.medias = self.provider.upload(
            medias,
            CONF.refresh_medias)
