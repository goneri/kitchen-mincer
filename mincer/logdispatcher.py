# -*- coding: utf-8 -*-
#
# Copyright 2014 eNovance SAS <licensing@enovance.com>
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

LOG = logging.getLogger(__name__)

MINCER_LOGDISPATCHER_NS = 'mincer.logdispatchers'


class Logdispatcher(object):
    """Dispatch the stack logs to the different logger backend."""

    @staticmethod
    def report_error(manager, entrypoint, exception):
        LOG.error("Error while loading logdispatcher %s", entrypoint)
        raise exception

    def __init__(self, environment, provider):
        self.logdispatchers = []
        for params in environment.logdispatchers_params():
            kwargs = dict(params=params, provider=provider)

            ld = driver.DriverManager(
                namespace=MINCER_LOGDISPATCHER_NS,
                name=params['driver'],
                invoke_on_load=True,
                on_load_failure_callback=self.report_error,
                invoke_kwds=kwargs).driver
            self.logdispatchers.append(ld)

    """Pass a log content to the different dispatchers.

    Args:
        name (str): a name associated to this content
        content (StringIO): a StringIO instance
    """
    def store(self, name, content):
        for ld in self.logdispatchers:
            ld.store(name, content)
