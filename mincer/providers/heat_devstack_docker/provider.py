# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel.boudjnah@enovance.com>
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


class HeatDevstackDocker(object):
    def __init__(self, params={}, identity={}, args={}):
        self.identity = identity
        self.args = args

    def create(self):
        identity = self.identity
        args = self.args
    # NB(chmouel): This is a sample method to see if things works
        if args.test:
            print("I will spawn a vm with the following credentials:\n\n"
                  "username: %s\n"
                  " tenant: %s\n"
                  " password: %s\n"
                  " url: %s\n" % (
                      identity['os_username'],
                      identity['os_tenant_name'],
                      identity['os_password'],
                      identity['os_auth_url']))

        print("I will spawn a vm")
