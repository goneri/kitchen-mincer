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

import abc

import six


class PluginActionBase(object):

    """The base class used by the actions."""

    six.add_metaclass(abc.ABCMeta)

    def __init__(self, refresh_medias, provider, params, medias, private_key):
        """Action constructor.

        :param refresh_medias: the medias to reupload
        :type refresh_medias: list
        :param provider: the provider to use
        :type provider: mincer.providers.heat.provider.Heat
        :param params: the parameters needed by serverspec
        :type params: list
        :param medias: list of Media objects associated to the driver
        :type medias: list
        :param private_key: the private key used to access the machine
        :type private_key: An Crypto.PublicKey.RSA key object

        """
        self._refresh_medias = refresh_medias
        self.provider = provider
        self.params = params
        self.medias = medias
        self._private_key = private_key

    @abc.abstractmethod
    def launch(self):
        """abc abstractmethod used to call the action

        :returns: True on success or False
        :rtype: Boolean

        """
        raise NotImplementedError("launch() has to be defined")
