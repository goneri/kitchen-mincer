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

import jinja2
from oslo.config import cfg
import six
import voluptuous

from mincer import media
import mincer.utils.fs_layer

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
MINCER_ACTIONS_NS = 'mincer.actions'


class Marmite(object):

    """This class represents the marmite

    it centralize all the access of the marmite's fields.
    """

    environments = {}

    def __init__(self, marmite_directory):
        """Marmite constructor

        :param marmite_dir: the path of the marmite directory
        :type marmite_dir: str
        :param extra_params: optional parameter to pass to Heat
        :type extra_params: dict
        """
        if marmite_directory is None:
            raise ValueError("'marmite_dir' argument is required")
        self.fs_layer = mincer.utils.fs_layer.FSLayer(marmite_directory)

        template_values = CONF.extra_params
        template_values['marmite_dir'] = marmite_directory
        try:
            self.marmite_tree = self.fs_layer.get_file(
                'marmite.yaml',
                template_values=template_values,
                load_yaml=True)
        except IOError as e:
            raise NotFound(e)
        except jinja2.exceptions.UndefinedError as e:
            raise InvalidTemplate(e)
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise InvalidTemplate(e)
        self._validate()

        self._application = Application(self.marmite_tree['application'])
        self.environments = {}
        for name in self.marmite_tree['environments']:
            self.environments[name] = Environment(
                name,
                self.marmite_tree['environments'][name])

    def _validate(self):
        """Validate the structure of the marmite."""
        All = voluptuous.All
        Required = voluptuous.Required
        Length = voluptuous.Length
        Extra = voluptuous.Extra

        schema = voluptuous.Schema({
            Required('description'): voluptuous.All(str, Length(min=5)),
            Required('environments'): dict,
            Required('application'): {
                Required('name'): str,
                Required('scenario'): [{
                    Required('driver'): str,
                    Required('description'): All(str, Length(min=5)),
                    Extra: object}]}})
        try:
            schema(self.marmite_tree)
        except voluptuous.MultipleInvalid as e:
            LOG.error("Failed to validate %s/marmite.yaml structure: %s" %
                      (self.fs_layer.base_dir, e))
            raise InvalidStructure()

    def description(self):
        """Return de description string of the marmite.

        :returns: description of the marmite
        :rtype: str

        """
        return self.marmite_tree['description']

    def application(self):
        """Return the application of the marmite.

        :returns: the application structure
        :rtype: dict

        """
        return self._application

    def environment(self, name):
        """Return the environment from the marmite.

        :returns: the environment
        :type: dict

        """
        return self.environments[name]


class Environment(object):

    """The object that describe the customer environment."""

    def __init__(self, name, environment_tree):
        """the Environment constructor

        :param name: the name of the environment
        :param environment_tree: the structure used to describe the environment
        :type environment_tree: dict()
        :returns: None
        :rtype: None

        """
        self.name = name
        self.tree = environment_tree

    def provider(self):
        """return the optionnal `provider` key.

        This key is used to describe the provider to use. _heat_ is the
        default value.

        :returns: the name of the provider driver to load
        :rtype: str

        """
        return self.tree.get('provider', 'heat')

    def provider_params(self):
        """return an optional `provider_params` key.

        :returns: the provider
        :rtype: dict

        """
        return self.tree.get('provider_params', {})

    def key_pairs(self):
        """Return the customer keypair

        :returns: a list of keypairs
        :rtype: dict

        """
        return self.tree.get('key_pairs', [])

    def floating_ips(self):
        """Return the floating IP to associate with the application.

        :returns: the floating IP
        :rtype: dict

        """
        return self.tree.get('floating_ips', {})

    def logdispatchers_params(self):
        """Return the logdispatchers

        :returns: the logdispatchers configured in the environment
        :rtype: list

        """
        return self.tree.get('logdispatchers', [])


class Application(object):

    """Object used to describe an Application."""

    def __init__(self, application_tree):
        """Application constructor

        :param application_tree: the data structure that describe the
        Application
        :type application_tree: dict
        :returns: None
        :rtype: None

        """
        self.application_tree = application_tree

    def name(self):
        """Return the name of the application.

        :returns: the name of the application
        :rtype: str

        """
        return self.application_tree['name']

    def medias(self):
        """Return the medias associated to the application.

        :returns: the medias
        :rtype: dict

        """
        ret = {}
        m = self.application_tree['medias']
        for k, v in six.iteritems(m):
            ret[k] = media.Media(k, v)
        return ret

    def scenario(self):
        """Return the scenario of the application.

        :returns: the actions of the scenario
        :rtype: list of action dict

        """
        scenario = []
        for action in self.application_tree['scenario']:
            scenario.append(action)
        return scenario


class NotFound(Exception):

    """Exception raised when an object is not found."""


class InvalidStructure(Exception):

    """Exception raised when a marmite is not valide."""


class InvalidTemplate(Exception):

    """Exception raised when a marmite has an invalid Jinja2 structure."""
