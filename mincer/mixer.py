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

import logging
import string

from Crypto.PublicKey import RSA
import six
from stevedore import driver

import mincer.credentials
import mincer.logdispatcher

LOG = logging.getLogger(__name__)


MINCER_PROVIDERS_NS = 'mincer.providers'
MINCER_ACTIONS_NS = 'mincer.actions'


class Mixer(object):

    """The Kitchen Mincer main class."""

    def __init__(self, marmite, args):
        """Constructor of the Mixer object

        :param marmite: directory to the marmite
        :type marmite: str
        :param args: The arguments returned by get_args()
        :type args: A argparse.Namespace instance
        :returns: None
        :rtype: None

        """
        self.args = args
        self.marmite = marmite
        self.credentials = mincer.credentials.Credentials(
            args.credentials_file)

    @staticmethod
    def report_error(manager, entrypoint, exception):
        """Log an error and rease an exception

        This method is called by Stevedore throught the
        on_load_failure_callback callback.

        :param manager: None, unused
        :type manager: None
        :param entrypoint: the entrypoint
        :type entrypoint: str
        :param exception: the raised exception
        :type exception: exception
        :returns: None
        :rtype: None

        """
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

    # TODO(Gonéri): should be moved in the Marmite object
    def _load_action(self, args, provider, private_key):

        kwargs = dict(args=args,
                      provider=provider,
                      private_key=private_key)

        return driver.DriverManager(
            namespace=MINCER_ACTIONS_NS,
            name=args['driver'],
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

    def test(self, env_name):
        """Validate a `marmite`

        This method is used associated to the `--test` parameter.

        :param env_name: the name of the environment
        :type env_name: str
        :returns: None
        :rtype: None

        """
        environment = self.marmite.environments[env_name]
        self._load_provider(environment)

    # TODO(Gonéri): I think we should move that in a mincer.utils class
    # or something similar.
    def _generate_key_pairs(self):
        """Generate ssh key pairs in OpenSSH format.

        :returns: a tuple of string for the key pairs in
        the format (private_key, public_key)
        :rtype: tuple

        """
        private_key = RSA.generate(2048)
        public_key = private_key.publickey()

        # Heat replaces carriage return by spaces then it's escaped
        r_private_key = string.replace(private_key.exportKey(), "\n", "\\n")
        r_public_key = string.replace(public_key.exportKey("OpenSSH"), "\n",
                                      "\\n")

        return r_private_key, r_public_key

    def _store_log(self, logs, environment, provider):
        """Record the logs

        :param logs: a dict of log content, the filename if the key
        :type logs: dict
        :param environment: the marmite environment structure
        :param provider: the provider object

        """
        # TODO(Gonéri): add a test for this case
        if not logs:
            return

        logdispatcher = mincer.logdispatcher.Logdispatcher(
            environment, provider)

        for name, content in six.iteritems(logs):
            logdispatcher.store(name, content)

    def bootstrap(self, env_name, refresh_medias):
        """Bootstrap the application.

        This method bootstraps the application, run the tests
        and store the logs.

        :param env_name: the name of the used environment
        :type env_name: str
        :param refresh_medias: the list of the medias to refresh
        :type refresh_medias: list
        """
        environment = self.marmite.environment(env_name)
        medias = self.marmite.application().medias()
        medias.update(environment.medias())

        for media_name in medias:
            LOG.info("media%s>", media_name)

        test_priv_key, test_pub_key = self._generate_key_pairs()

        provider = self._load_provider(environment)

        provider.connect(self.credentials.get())
        # TODO(Gonéri): the media upload should we done using an action
        provider.medias = provider.upload(medias, refresh_medias)
        provider.register_pub_key(test_pub_key)
        provider.ssh_client._set_priv_key(test_priv_key)
        output_fip = provider.register_floating_ips(environment.floating_ips())

        scenario = []
        for step in self.marmite.application().scenario():
            action = self._load_action(step, provider, test_priv_key)
            scenario.append(action)

        for fip_name in output_fip:
            LOG.info("Floating ip '%s' : '%s'" %
                     (fip_name, output_fip[fip_name]))

        for action in scenario:
            LOG.info("Running: %s" % action.description)
            logs = action.launch()
            self._store_log(logs, environment, provider)
            provider.watch_running_checks()

        if not self.args.preserve:
            provider.cleanup()
