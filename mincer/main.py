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

logging.basicConfig(level=logging.INFO)


class AppendExtraParams(argparse.Action):
    """A the AppendExtraParams action to argparse. This action
    expects the parameter to be in the key=value format.
    It adds the the key/value in a dictionary.
    This is useful to allow extra parameters to be specified multiple times.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        (k, v) = values.split('=')
        items = copy.copy(argparse._ensure_value(namespace, self.dest, {}))
        items[k] = v
        setattr(namespace, self.dest, items)


def get_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Target to run")
    parser.add_argument("--extra_params", action=AppendExtraParams,
                        help="Additional parameters")
    parser.add_argument("--test", action="store_true",
                        help="Enter the test mode")
    parser.add_argument('--refresh-medias', nargs='+',
                        help="medias to refresh")
    parser.add_argument("--preserve", action="store_true",
                        help="Do not clean the stack at end of the process")
    parser.add_argument("marmite_directory", help="Main marmite directory.")
    return parser.parse_args(args=args)


def main():
    args = get_args()
    m = mixer.Mixer(marmite.Marmite(args.marmite_directory), args)
    if args.test:
        m.test(args.target)
    elif args.target:
        m.bootstrap(args.target, args.refresh_medias or [])

if __name__ == '__main__':
    main()
