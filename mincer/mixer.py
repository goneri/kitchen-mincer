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

from stevedore import driver

from mincer import marmite

MINCER_PROVIDERS_NS = 'mincer.providers'


class Mixer(object):
    def __init__(self, marmite_dir, args):
        self.args = args
        self.marmite = marmite.Marmite(marmite_dir)

    @staticmethod
    def report_error(manager, entrypoint, exception):
        #TODO(chmouel): s/print/logging system/
        print("Error while loading provider %s" % entrypoint)
        raise exception

    def start_provider(self, env):

        environments = self.marmite.environments()
        identity = environments.identity(env)
        provider = environments.provider(env)
        provider_params = environments.provider_params(env)

        kwargs = dict(params=provider_params,
                      args=self.args,
                      identity=identity)

        provider = driver.DriverManager(
            namespace=MINCER_PROVIDERS_NS,
            name=provider,
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

        #TODO(chmouel): is this the entry point?
        provider.create()
