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

from oslo.config import cfg
from stevedore import driver

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
MINCER_PROVIDERS_NS = 'mincer.providers'


def get(environment):
    """Load the provider."""
    kwargs = dict(params=environment.provider_params(), args=CONF)

    return driver.DriverManager(
        namespace=MINCER_PROVIDERS_NS,
        name=environment.provider(),
        invoke_on_load=True,
        on_load_failure_callback=report_error,
        invoke_kwds=kwargs).driver


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
