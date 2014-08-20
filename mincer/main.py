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
import copy
import logging

from mincer import marmite
from mincer import mixer


class AppendExtraParams(argparse.Action):

    """The AppendExtraParams action to argparse.

    This action expects the parameter to be in the `key=value` format.
    It adds the key/value in a dictionary.
    This is useful to allow extra parameters to be specified multiple times.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """argparse.Action callback

        :param parser: unused
        :type parse: None
        :param namespace: the command-line argument object
        :type namespace: argeparse.Namespace instance
        :param values: a list of value
        :type values: list() or str()
        :param option_string: unused parameter
        :type option_string: None
        :returns: None
        :rtype: None

        """
        (k, v) = values.split('=')
        items = copy.copy(argparse._ensure_value(namespace, self.dest, {}))
        items[k] = v
        setattr(namespace, self.dest, items)


def get_args(args=None):
    """Parse the argument

    In a script, parse_args() will typically be called with no arguments,
    and the ArgumentParser will automatically determine the command-line
    arguments from sys.argv.

    :param args: optional list of argument
    :returns: object holding attributes
    :rtype: argparse.Namespace

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Target to run")
    parser.add_argument("--credentials-file", help="Adjust the location of "
                        "the credential file, default is "
                        "~/.config/mincer/credentials.yaml")
    parser.add_argument("--debug", action="store_true",
                        help="Debug mode")
    parser.add_argument("--extra_params", action=AppendExtraParams,
                        help="Additional parameters", default={})
    parser.add_argument("--test", action="store_true",
                        help="Enter the test mode")
    parser.add_argument('--refresh-medias', nargs='+',
                        help="medias to refresh")
    parser.add_argument("--preserve", action="store_true",
                        help="Do not clean the stack at end of the process")
    parser.add_argument("marmite_directory", help="Main marmite directory.")
    return parser.parse_args(args=args)


def setup_logging(debug):
    """Configure the logging class

    :param debug: boolean to enable debugging
    :returns: None
    :rtype: None

    """
    log_lvl = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(levelname)s (%(module)s) %(message)s",
        level=log_lvl)
    logging.getLogger('iso8601').setLevel(logging.DEBUG)

    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    iso_log = logging.getLogger("iso8601")
    iso_log.setLevel(logging.WARNING)


def main():
    """The entry point of the application.

    :returns: None
    :rtype: None

    """
    args = get_args()

    setup_logging(args.debug)

    m = mixer.Mixer(marmite.Marmite(args.marmite_directory,
                                    extra_params=args.extra_params), args)
    if args.test:
        m.test(args.target)
    elif args.target:
        m.bootstrap(args.target, args.refresh_medias or [])

if __name__ == '__main__':
    main()
