# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@enovance.com>
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

from stevedore import driver
import yaml

from mincer import constants
from mincer import exceptions


class Mixer(object):
    def __init__(self, marmite_dir, args):
        self.args = args
        if not os.path.exists(marmite_dir):
            raise exceptions.NotFound(
                "Marmite %s was not found on the fs" % marmite_dir)

        self.marmite_dir = marmite_dir
        self.yaml_tree = self._load_file(os.path.join(self.marmite_dir,
                                                      "marmite.yaml"))

    def _load_file(self, filename):
        with open(filename, 'r') as f:
            return yaml.load(f)

    def _check_provider_is_here(self, env):
        if env not in self.yaml_tree['environments']:
            raise exceptions.NotFound(
                "Provider %s was not found in yaml file" % (env))

    def report_error(self, manager, entrypoint, exception):
        #TODO(chmouel): s/print/logging system/
        print("Error while loading provider %s" % entrypoint)
        raise exception

    def get_method_configuration(self, method):
        cfg = self.yaml_tree.get('methods')
        if cfg and method in cfg:
            return cfg[method]
        fname = os.path.join(self.marmite_dir, 'methods', method)
        if os.path.exists(fname):
            return yaml.load(open(fname, 'r'))

        # TODO(chmouel): May have some methods tha thav eno configuration
        raise exceptions.NotFound(
            "Cannot find configuration for method: %s" % method)

    def get_identity(self, env):
        ret = {}
        for key in self.yaml_tree['environments'][env].keys():
            if not key.startswith('identity'):
                continue

            value = self.yaml_tree['environments'][env][key]
            if ('identities' in self.yaml_tree and
                value in self.yaml_tree['identities']):
                ret = self.yaml_tree['identities'][value]
                break

            fname = os.path.join(self.marmite_dir,
                                 'identities',
                                 self.yaml_tree['environments'][env][key])

            if not os.path.exists(fname):
                raise exceptions.NotFound(
                    "Identity %s was not found in yaml file" % (key))

            ret = yaml.load(open(fname, 'r'))

        for row in ret:
            if ret[row].startswith("$"):
                ret[row] = os.environ.get(
                    ret[row].replace('$', ''))
        return ret

    def start_provider(self, env):
        self._check_provider_is_here(env)

        identity = self.get_identity(env)
        method = self.yaml_tree['environments'][env]['method']
        method_configuration = self.get_method_configuration(method)

        kwargs = dict(method_configuration=method_configuration,
                      args=self.args,
                      identity=identity)

        #TODO(chmouel): May need some lazy loading but let's do like
        # that for now
        return driver.DriverManager(
            namespace=constants.MINCER_PROVIDERS_NS,
            name=self.yaml_tree['environments'][env]['method'],
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver
