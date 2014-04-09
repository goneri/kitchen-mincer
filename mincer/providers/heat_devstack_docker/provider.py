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


def main(method_configuration={}, identity={}, args={}):
    # NB(chmouel): This is a sample method to see if things works
    if args.test:
        print("I will use spawn a vm with tenant %s "
              "and password %s to url %s") % (
                  identity['os_tenant_name'],
                  identity['os_password'],
                  identity['os_auth_url'],)

        print("I will spawn a vm from a snapshot called" + (
            method_configuration['image']))
        print("And I will launch the heat file " + (
            method_configuration['heat_file']))
