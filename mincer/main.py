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

from mincer import mixer


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Target to run")
    parser.add_argument("--test", action="store_true",
                        help="Enter the test mode")
    parser.add_argument("marmite_directory", help="Main marmite directory.")
    args = parser.parse_args(args=args)
    m = mixer.Mixer(args.marmite_directory, args)
    if args.test:
        m.test(args.target)
    elif args.target:
        m.bootstrap(args.target)
