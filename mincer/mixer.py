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
from stevedore import driver

from mincer import marmite
from mincer import mediamanager  # noqa


logger = logging.getLogger(__name__)


MINCER_PROVIDERS_NS = 'mincer.providers'


class Mixer(object):
    def __init__(self, marmite_dir, args):
        self.args = args
        self.marmite = marmite.Marmite(marmite_dir)

    @staticmethod
    def report_error(manager, entrypoint, exception):
        logger.error("Error while loading provider %s" % entrypoint)
        raise exception

    def _load_provider(self, environment):

        kwargs = dict(params=environment.provider_params(), args=self.args)

        # TODO(Gonéri)
        import providers.heat
        return providers.heat.Heat(**kwargs)

        return driver.DriverManager(
            namespace=MINCER_PROVIDERS_NS,
            name=environment.provider(),
            invoke_on_load=True,
            on_load_failure_callback=self.report_error,
            invoke_kwds=kwargs).driver

    def test(self, env_name):
        environment = self.marmite.environments[env_name]
        self._load_provider(environment)

    def bootstrap(self, env_name):

        environment = self.marmite.environments[env_name]
        mm = mediamanager.MediaManager()
        medias = self.marmite.application().medias()
        medias.update(environment.medias())

        for name in medias:
            # Register the medias in the Media Manager
            mm.append(mediamanager.Media(name, medias[name]))

        for media in mm:
            logger.info("media%s> %s (%s)" % (
                media.name,
                media.getPath(),
                media.checksum))

        provider = self._load_provider(environment)
        provider.connect(environment.identity())
        provider.upload(mm)
        provider.register_key_pairs(environment.key_pairs())
        provider.register_floating_ips(environment.floating_ips())
        provider.create()
