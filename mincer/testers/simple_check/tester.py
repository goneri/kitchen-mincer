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
import string
import subprocess

LOG = logging.getLogger(__name__)


class SimpleCheck(object):

    def __init__(self, provider, params):
        self.provider = provider
        self.params = params

    def _save_test_results(self, result, error_code):
        with open("/tmp/test_results", "wb") as file_result:
            file_result.write(result)
            if error_code == 0:
                file_result.write("\n ===> Test success ! \o/\n\n")
            else:
                file_result.write("\n ===> Test failed !\n")

    def _run_script_test(self, target, machine_ip):
        command = string.Template(self.params[target]).\
            substitute({"IP": machine_ip})
        process = subprocess.Popen(command.split(),
                                   stdout=subprocess.PIPE)
        stdout = process.communicate()[0]
        error_code = process.returncode
        self._save_test_results(stdout, error_code)

    def launch(self):

        for machine in self.provider.get_machines():
            for target in self.params:
                if target == '_ALL_' or target == machine["name"]:
                    machine_ip = machine["primary_ip_address"]
                    self._run_script_test(target, machine_ip)
                else:
                    raise TargetNotFound("target '%s' not found" % target)


class TargetNotFound(Exception):
    """Exception raised when an object is not found."""
