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


class NotFound(Exception):

    """Exception raised when an element is missing."""

    pass


class AuthorizationFailure(Exception):

    """Raised when connection to OpenStack API has failed."""


class InstanceNameFromTemplateNotFoundInStack(Exception):

    """Raised when a command reference an unexisting instance name."""
