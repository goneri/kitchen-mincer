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

import codecs

import jinja2
import requests
import yaml


class FSLayer(object):

    """A file abstraction layer."""

    def __init__(self, base_dir):
        """FSLayer constructor."""
        self.base_dir = base_dir
        self.remote = False

        if base_dir[0:8] == 'https://' or base_dir[0:7] == 'http://':
            self.remote = True

        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)

    def get_file(self, filename, template_values=None, load_yaml=False):
        """Return the content of a given file."""
        if not self.remote:
            content = codecs.open(
                self.base_dir + '/' + filename, 'r', 'utf-8').read()
        else:
            r = requests.get(self.base_dir + '/' + filename)
            content = r.text

        if template_values is not None:
            template = self.env.from_string(content)
            content = template.render(template_values)

        if load_yaml is True:
            content = yaml.load(content)

        return(content)
