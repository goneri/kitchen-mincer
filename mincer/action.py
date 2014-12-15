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

    def __init__(self, args, provider):
        """Action constructor.

        :param args: the action data structure
        :type args: dict
        :param providers: the Cloud provider
        :type provider: a provider instance

        """
        self.args = args
        self.provider = provider
        self.description = self.args.get('description', "No description")

    @abc.abstractmethod
    def launch(self, marmite):
        """abc abstractmethod used to call the action

        :param marmite: the marmite object
        :type marmite: Marmite instance

        """
        raise NotImplementedError("launch() has to be defined")
