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
import sys

from oslo.config import cfg

import mincer.credentials
import mincer.marmite
import mincer.provider

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

OPTS = [
    cfg.StrOpt('target', default='devtest',
               help='Target to run'),
    cfg.StrOpt('credentials_file',
               help="Adjust the location of "
               "the credential file, default is", default=None),
    cfg.BoolOpt('debug', default=False,
                help='Debug mode'),
    cfg.DictOpt('extra_params',
                help="Additional parameters", default={}),
    cfg.ListOpt('refresh_medias', help="medias to refresh", default=[]),
    cfg.BoolOpt('preserve',
                help="Do not clean the stack at end of the process",
                default=False),
    cfg.StrOpt('marmite_directory', help="Main marmite directory."),
]

opt_group = cfg.OptGroup(name='mincer',
                         title='The options of the mincer')
CONF.register_group(opt_group)
CONF.register_opts(OPTS, opt_group)
CONF.register_cli_opts(OPTS)


def setup_logging():
    """Configure the logging class

    :param debug: boolean to enable debugging
    :returns: None
    :rtype: None

    """
    log_lvl = logging.DEBUG if CONF.debug else logging.INFO
    logging.basicConfig(
        format="%(levelname)s (%(module)s) %(message)s",
        level=log_lvl)
    logging.getLogger('iso8601').setLevel(logging.DEBUG)

    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    iso_log = logging.getLogger("iso8601")
    iso_log.setLevel(logging.WARNING)


def bootstrap():
    """Bootstrap the application.

    This method bootstraps the application, run the tests
    and store the logs.

    """
    marmite = mincer.marmite.Marmite(
        marmite_directory=CONF.marmite_directory)
    environment = marmite.environment(CONF.target)
    provider = mincer.provider.get(environment)

    try:
        credentials = mincer.credentials.Credentials()
        provider.connect(credentials.get())
        for action in marmite.application().scenario():
            action["marmite"] = marmite
            provider_function_to_call = action["driver"]
            provider_function = getattr(provider,
                                        provider_function_to_call)
            provider_function(**action)
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


def main(argv=sys.argv):
    """The entry point of the application."""
    CONF(argv[1:], project="mincer")
    setup_logging()
    bootstrap()

if __name__ == '__main__':
    main()
