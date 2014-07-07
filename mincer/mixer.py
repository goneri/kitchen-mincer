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


from Crypto.PublicKey import RSA
import logging

from stevedore import driver

import mincer.logdispatcher

LOG = logging.getLogger(__name__)


MINCER_PROVIDERS_NS = 'mincer.providers'
MINCER_TESTS_NS = 'mincer.tests'


class Mixer(object):
    def __init__(self, marmite, args):
        self.args = args
        self.marmite = marmite

    @staticmethod
    def report_error(manager, entrypoint, exception):
        LOG.error("Error while loading provider %s", entrypoint)
        raise exception

    def _load_provider(self, environment):

        kwargs = dict(params=environment.provider_params(), args=self.args)

        return driver.DriverManager(
            namespace=MINCER_PROVIDERS_NS,
            name=environment.provider(),
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

    def _load_test(self, test, provider, refresh_medias, private_key):

        kwargs = dict(provider=provider, refresh_medias=refresh_medias,
                      params=test.params, medias=test.medias,
                      private_key=private_key)

        return driver.DriverManager(
            namespace=MINCER_TESTS_NS,
            name=test.driver(),
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

    def test(self, env_name):
        environment = self.marmite.environments[env_name]
        self._load_provider(environment)

    def _generate_key_pairs(self):
        """Generate ssh key pairs in OpenSSH format.

        :returns: a tuple of string for the key pairs in
        the format (private_key, public_key)
        :rtype: tuple
        """

        private_key = RSA.generate(2048)
        public_key = private_key.publickey()
        return private_key.exportKey(), public_key.exportKey("OpenSSH")

    def bootstrap(self, env_name, refresh_medias):
        """Bootstrap the application."""
        environment = self.marmite.environment(env_name)
        medias = self.marmite.application().medias()
        medias.update(environment.medias())

        for media_name in medias:
            LOG.info("media%s>", media_name)

        test_priv_key, test_pub_key = self._generate_key_pairs()

        provider = self._load_provider(environment)
        logdispatcher = mincer.logdispatcher.Logdispatcher(
            environment, provider)
        # TODO(Gonéri): logdispatcher object should be consumed only
        # from mixer.py. To do so, we must collect the log directly here
        provider.logdispatcher = logdispatcher
        provider.connect(environment.identity())
        provider.launch_application(
            self.marmite.application().name(),
            provider.upload(medias, refresh_medias),
            provider.register_key_pairs(environment.key_pairs(), test_pub_key),
            provider.register_floating_ips(environment.floating_ips()))

        for test in self.marmite.testers():
            test_instance = self._load_test(test, provider, refresh_medias,
                                            test_priv_key)
            test_instance.launch()

        if not self.args.preserve:
            provider.cleanup_application()
