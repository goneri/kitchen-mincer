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
import six

import yaml

from mincer import media


class Marmite(object):
    """This class represents the marmite, it centralize all the access of the
    marmite's fields.
    """

    environments = {}

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
        self.marmite_tree = yaml.load(open(marmite_path, 'rb'))
        self._application = Application(self.marmite_tree['application'])
        self.environments = {}
        for name in self.marmite_tree['environments']:
            self.environments[name] = Environment(
                name,
                self.marmite_tree['environments'][name])

    def description(self):
        try:
            return self.marmite_tree['description']
        except KeyError:
            raise NotFound("'description' not found")

    def application(self):
        return self._application

    def environment(self, name):
        try:
            return self.environments[name]
        except KeyError:
            raise NotFound("environment '%s' not found" % name)

    def testers(self):
        try:
            tests_names = self.marmite_tree['testers']
        except KeyError:
            raise NotFound("'testers' section is missing in the marmite")

        tests = []
        for test_name in tests_names:
            tests.append(Test(self.marmite_tree['testers'][test_name],
                              test_name))
        return tests


class Environment(object):
    def __init__(self, name, environment_tree):
        self.name = name
        self.tree = environment_tree

    def provider(self):
        return self.tree.get('provider', 'heat')

    def provider_params(self):
        return self.tree.get('provider_params', {})

    def identity(self):
        credentials = {}
        identities = self.tree['identity']
        for credential, value in identities.items():
            if value.startswith("$"):
                credentials[credential] = os.environ.get(value[1:])
                if credentials[credential] is None:
                    raise ValueError("Env variable '%s' not set" % value)
            else:
                credentials[credential] = value
        return credentials

    def medias(self):
        ret = {}
        for k, v in self.tree.get('medias', {}).iteritems():
            ret[k] = media.Media(k, v)
        return ret

    def key_pairs(self):
        return self.tree.get('key_pairs', [])

    def floating_ips(self):
        return self.tree.get('floating_ips', [])

    def logdispatchers_params(self):
        return self.tree.get('logdispatchers', [])


class Application(object):
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
        ret = {}
        m = self.application_tree.get('medias', {})
        for k, v in six.iteritems(m):
            ret[k] = media.Media(k, v)
        return ret


class Test(object):
    def __init__(self, test_tree, test_name):
        self.test_tree = test_tree
        self.test_name = test_name

    def driver(self):
        try:
            return self.test_tree['driver']
        except KeyError:
            raise NotFound("test '%s' has no 'driver' key" % self.test_name)

    def params(self):
        try:
            return self.test_tree['params']
        except KeyError:
            raise NotFound("test '%s' has no 'params' key" % self.test_name)

    def medias(self):
        ret = {}
        for k, v in self.test_tree.get('medias', {}).iteritems():
            ret[k] = media.Media(k, v)
        return ret


class NotFound(Exception):
    """Exception raised when an object is not found."""
