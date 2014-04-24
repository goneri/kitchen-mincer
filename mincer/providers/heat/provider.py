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

import heatclient.client as heatclient
import heatclient.exc as heatclientexc
import keystoneclient.v2_0


class ProviderExceptionn(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class AlreadyExisting(Exception):
    def __init__(self):
        raise ProviderExceptionn("Stack already existing")


class Heat(object):
    def __init__(self, params={}, identity={}, args={}):
        self.params = params
        self.args = args

        if identity:
            self.keystone = keystoneclient.v2_0.Client(
                auth_url=identity['os_auth_url'],
                username=identity['os_username'],
                password=identity['os_password'],
                tenant_name=identity['os_tenant_name'])

    def _get_heat_template(self):
        with open(self.args.marmite_directory + "/heat.yaml") as file:
            return file.read()

    def create(self):

        heat_endpoint = self.keystone.service_catalog.url_for(
            service_type='orchestration')
        self.heat = heatclient.Client('1', endpoint=heat_endpoint,
                                      token=self.keystone.auth_token)

        hot_template = self._get_heat_template()

        try:
            self.heat.stacks.create(
                stack_name='zoubida',
                parameters={'key_name': 'stack_os-ci-test7'},
                template=hot_template, timeout_mins=60)
        except heatclientexc.HTTPConflict:
            print("Stack creation failed because of a conflict")
            raise AlreadyExisting
