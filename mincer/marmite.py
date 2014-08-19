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

import logging
import os

import jinja2
import six
import voluptuous
import yaml

from mincer import media

LOG = logging.getLogger(__name__)


class Marmite(object):
    """This class represents the marmite

    it centralize all the access of the marmite's fields.
    """

    environments = {}

    def __init__(self, marmite_dir, extra_params={}):

        """Marmite constructor

        :param marmite_dir: the path of the marmite directory
        :type group_id: str
        """
        if marmite_dir is None:
            raise ValueError("'marmite_dir' argument is required")
        self.marmite_dir = marmite_dir

        template_loader = jinja2.FileSystemLoader(searchpath=marmite_dir)
        env = jinja2.Environment(loader=template_loader,
                                 undefined=jinja2.StrictUndefined)
        try:
            template = env.get_template("marmite.yaml")
        except jinja2.exceptions.TemplateNotFound:
            raise NotFound()
        except jinja2.exceptions.TemplateSyntaxError as e:
            LOG.error("Invalid template syntax in %s/marmite.yaml: %s" % (
                marmite_dir, e))
            raise InvalidStructure()
        marmite = template.render(extra_params)
        self.marmite_tree = yaml.load(marmite)
        self._validate()

        self._application = Application(self.marmite_tree['application'])
        self.environments = {}
        for name in self.marmite_tree['environments']:
            self.environments[name] = Environment(
                name,
                self.marmite_tree['environments'][name])

    def _validate(self):
        All = voluptuous.All
        Required = voluptuous.Required
        Length = voluptuous.Length

        schema = voluptuous.Schema({
            Required('description'): voluptuous.All(str, Length(min=5)),
            Required('environments'): dict,
            Required('application'): {
                Required('name'): str,
                Required('medias'): dict,
                Required('scenario'): [{
                    Required('driver'): str,
                    Required('params'): All(),
                    Required('description'): All(str, Length(min=5))}]}})
        try:
            schema(self.marmite_tree)
        except voluptuous.MultipleInvalid as e:
            LOG.error("Failed to validate %s/marmite.yaml structure: %s" %
                      (self.marmite_dir, e))
            raise InvalidStructure()

    def description(self):
        return self.marmite_tree['description']

    def application(self):
        return self._application

    def environment(self, name):
        return self.environments[name]


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
        try:
            for k, v in self.tree['medias'].iteritems():
                ret[k] = media.Media(k, v)
        except KeyError:
            pass
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
        return self.application_tree['name']

    def medias(self):
        ret = {}
        m = self.application_tree['medias']
        for k, v in six.iteritems(m):
            ret[k] = media.Media(k, v)
        return ret

    def scenario(self):
        scenario = []
        for action in self.application_tree['scenario']:
            scenario.append(Action(action))
        return scenario


class Action(object):
    def __init__(self, tree):
        self.tree = tree

    def driver(self):
        return self.tree['driver']

    def params(self):
        return self.tree['params']


class NotFound(Exception):
    """Exception raised when an object is not found."""


class InvalidStructure(Exception):
    """Exception raised when a marmite is not valide."""
