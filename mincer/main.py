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
import argparse
import os

import stevedore
import yaml

from mincer import exceptions


class Main(object):
    def __init__(self, marmite_dir):
        if not os.path.exists(marmite_dir):
            raise exceptions.NotFound(
                "Marmite %s was not found on the fs" % marmite_dir)

        self.marmite_dir = marmite_dir
        self.yaml_tree = self._load_file(os.path.join(self.marmite_dir,
                                                      "marmite.yaml"))
        self.providers = stevedore.extension.ExtensionManager(
            namespace='mincer.providers')

    def _load_file(self, filename):
        with open(filename, 'r') as f:
            return yaml.load(f)

    def _check_provider_is_here(self, env):
        if env not in self.yaml_tree:
            raise exceptions.NotFound(
                "Provider %s was not found in yaml file" % (env))

    def get_identity(self, env):
        ret = {}
        for key in self.yaml_tree[env].keys():
            if key.startswith('identity') or key.startswith('identities'):
                fname = os.path.join(self.marmite_dir,
                                     'identities', self.yaml_tree[env][key])
                with open(fname, 'r') as f:
                    ret.update(yaml.load(f))
        return ret

    def start_provider(self, env):
        self._check_provider_is_here(env)

        identities = self.get_identity(env)
        provider = None
        for p in self.providers:
            if p.name == self.yaml_tree[env]['method']:
                provider = p.plugin

        if not provider:
            raise exceptions.ProviderNotFound()

        return provider.main(configuration=self.yaml_tree[env],
                             identities=identities)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Target to run")
    parser.add_argument("marmite_file", help="Main marmite directory.")
    args = parser.parse_args(args=args)
    m = Main(args.marmite_file)
    m.start_provider(args.target)

if __name__ == '__main__':
    main(["../samples/wordpress-marmite/", "--target", "devtest"])
