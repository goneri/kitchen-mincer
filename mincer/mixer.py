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

from oslo.config import cfg
import six
from stevedore import driver

import mincer.credentials
import mincer.exceptions
import mincer.logdispatcher
from mincer import marmite

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

MINCER_PROVIDERS_NS = 'mincer.providers'


class Mixer(object):

    """The Kitchen Mincer main class."""

    def __init__(self):
        """Constructor of the Mixer object

        :returns: None

        """
        self.marmite = marmite.Marmite(
            marmite_directory=CONF.marmite_directory)
        self.credentials = mincer.credentials.Credentials()

    @staticmethod
    def report_error(manager, entrypoint, exception):
        """Log an error and raise an exception

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

        kwargs = dict(params=environment.provider_params(), args=CONF)

        return driver.DriverManager(
            namespace=MINCER_PROVIDERS_NS,
            name=environment.provider(),
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

    def test(self):
        """Validate a `marmite`

        This method is used associated to the `--test` parameter.

        :param env_name: the name of the environment
        :type env_name: str
        :returns: None
        :rtype: None

        """
        environment = self.marmite.environments[CONF.test]
        self._load_provider(environment)

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

    def bootstrap(self):
        """Bootstrap the application.

        This method bootstraps the application, run the tests
        and store the logs.

        """
        environment = self.marmite.environment(CONF.target)
        provider = self._load_provider(environment)

        try:
            provider.connect(self.credentials.get())

            for action in self.marmite.scenario:
                LOG.info("Running: %s" % action.description)
                logs = action.launch(marmite=self.marmite, provider=provider)
                self._store_log(logs, environment, provider)
                provider.watch_running_checks()
        except mincer.exceptions.AuthorizationFailure as e:
            LOG.exception(e)
            LOG.error("Connection failed: Authorization failure")
            raise StandardError()
        except mincer.exceptions.InstanceNameFromTemplateNotFoundInStack as e:
            LOG.error(e)
            raise StandardError()
        except Exception as e:
            LOG.exception(e)
            LOG.error("Internal error")
            raise StandardError()
        finally:
            if not CONF.preserve:
                LOG.debug("Cleaning the tenant")
                provider.cleanup()
