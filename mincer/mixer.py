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
    def __init__(self, marmite_dir):
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
        if env not in self.yaml_tree:
            raise exceptions.NotFound(
                "Provider %s was not found in yaml file" % (env))

    def report_error(self, manager, entrypoint, exception):
        #TODO(chmouel): s/print/logging system/
        print("Error while loading provider %s" % entrypoint)
        raise exception

    def get_identity(self, env):
        ret = {}
        for key in self.yaml_tree[env].keys():
            if key.startswith('identity') or key.startswith('identities'):
                fname = os.path.join(self.marmite_dir,
                                     'identities', self.yaml_tree[env][key])
                with open(fname, 'r') as f:
                    ret.update(yaml.load(f))

        for identity in ret:
            for row in ret[identity]:
                if ret[identity][row].startswith("$"):
                    ret[identity][row] = os.environ.get(
                        ret[identity][row].replace('$', ''))
        return ret

    def start_provider(self, env):
        self._check_provider_is_here(env)
        identities = self.get_identity(env)

        kwargs = dict(configuration=self.yaml_tree[env],
                      identities=identities)

        #TODO(chmouel): May need some lazy loading but let's do like
        # that for now
        return driver.DriverManager(
            namespace=constants.MINCER_PROVIDERS_NS,
            name=self.yaml_tree[env]['method'],
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver
