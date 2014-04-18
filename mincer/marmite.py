# -*- coding: utf-8 -*-
# Author: eNovance developers <dev@enovance.com>
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

import os

import yaml


class Marmite(object):
    """This class represents the marmite, it centralize all the access of the
    marmite's fields.
    """

    def __init__(self, marmite_dir):

        """:param marmite_dir: the path of the marmite directory
        :type group_id: str
        """
        if marmite_dir is None:
            raise ValueError("'marmite_dir' argument is required")
        self.marmite_dir = marmite_dir
        marmite_path = os.path.join(self.marmite_dir, "marmite.yaml")
        if not os.path.exists(marmite_path):
            raise NotFound("Marmite file '%s'" % marmite_path)
        self.marmite_tree = yaml.load(open(marmite_path, 'r'))

    def description(self):
        try:
            return self.marmite_tree['description']
        except KeyError:
            raise NotFound("'description' not found")

    def environments(self):
        """Returns the environments.

        :returns: all environments specified in the marmite file
        :rtype: Environments
        """
        try:
            return Environments(self.marmite_tree['environments'])
        except KeyError:
            raise NotFound("'environments' not found")

    def application(self):
        return Application(self.marmite_tree['application'])

    def medias(self):
        try:
            return self.marmite_tree['medias']
        except KeyError:
            raise NotFound("'medias' not found")


class Environments(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Environments, cls).__new__(cls,
                                                             *args,
                                                             **kwargs)
        return cls._instance

    def __init__(self, environments_tree):
        self.environments_tree = environments_tree

    def provider(self, environment):
        try:
            return self.environments_tree[environment]['provider']
        except KeyError:
            return 'heat'

    def provider_params(self, environment):
        try:
            return self.environments_tree[environment]['provider_params']
        except KeyError:
            return dict()

    def identity(self, environment):
        credentials = {}
        identities = self.environments_tree[environment]['identity']
        for credential, value in identities.items():
            if value.startswith("$"):
                credentials[credential] = os.environ.get(value[1:])
                if credentials[credential] is None:
                    raise ValueError("Env variable '%s' not set" % value)
            else:
                credentials[credential] = value
        return credentials

    def ip_pool(self, environment):
        try:
            return self.environments_tree[environment]['ip_pool']
        except KeyError:
            raise NotFound("'%s, ip_pool' not found" % environment)


class Application(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Application, cls).__new__(cls,
                                                            *args,
                                                            **kwargs)
        return cls._instance

    def __init__(self, application_tree):
        self.application_tree = application_tree

    def name(self):
        try:
            return self.application_tree['name']
        except KeyError:
            raise NotFound("'name' not found")

    def params(self):
        try:
            return self.application_tree['params']
        except KeyError:
            raise NotFound("'params' not found")

    def medias(self):
        try:
            return self.application_tree['medias']
        except KeyError:
            raise NotFound("'medias' not found")


class NotFound(Exception):
    """Exception raised when an object is not found."""
