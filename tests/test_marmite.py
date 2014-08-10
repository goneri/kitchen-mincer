# -*- coding: utf-8 -*-
# Author: eNovance developers <dev@enovance.com>
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

from mincer import marmite
from mincer import media

import mock
import six
import testtools

_OS_AUTH_VAR = ("os_auth_url", "os_username", "os_password", "os_tenant_name")
_PROVIDERS = ("heat", )


class TestMarmite(testtools.TestCase):
    """Test the Wordpress marmite.

    This unit tests are all done against the wordpress marmite
    which is currently the reference marmite.
    """

    def setUp(self):
        super(TestMarmite, self).setUp()
        self.marmite = marmite.Marmite("./samples/wordpress")

    def test_marmite_init_exception(self):
        self.assertRaises(ValueError, marmite.Marmite, None)
        self.assertRaises(marmite.NotFound, marmite.Marmite, "/tmp")

    def test_description(self):
        self.assertIsNotNone(self.marmite.description())

    def test_description_exception(self):
        del self.marmite.marmite_tree["description"]
        self.assertRaises(marmite.NotFound, self.marmite.description)

    @mock.patch('mincer.marmite.os.environ', {"OS_TENANT_NAME": "tenant",
                                              "OS_AUTH_URL": "auth_url",
                                              "OS_USERNAME": "username",
                                              "OS_PASSWORD": "password"})
    def test_environment(self):
        devtest_env = self.marmite.environment("devtest")
        self.assertIsNotNone(devtest_env)
        self.assertIsInstance(devtest_env,
                              marmite.Environment)
        self.assertTrue(devtest_env.provider() in _PROVIDERS)
        self.assertIsNotNone(devtest_env.identity())
        for auth_var in _OS_AUTH_VAR:
            self.assertTrue(auth_var in devtest_env.identity())

        self.assertIsNotNone(devtest_env.medias())
        for media_name, t_media in six.iteritems(devtest_env.medias()):
            self.assertIsInstance(t_media, media.Media)

        self.assertIn("stack_os_ci-test7", devtest_env.key_pairs())
        self.assertIn("public_wordpress_ip", devtest_env.floating_ips())
        logdispatcher_0 = devtest_env.logdispatchers()[0]
        self.assertTrue("name", logdispatcher_0)
        self.assertTrue("driver", logdispatcher_0)

    def test_environment_exception(self):
        self.assertRaises(marmite.NotFound, self.marmite.environment, "kikoo")

    @mock.patch('mincer.marmite.os.environ', {"OS_TENANT_NAME": "tenant",
                                              "OS_AUTH_URL": "auth_url",
                                              "OS_USERNAME": "username",
                                              "OS_PASSWORD": "password"})
    def test_identity_with_env_variables(self):
        devtest_identity = self.marmite.environment("devtest").identity()
        self.assertEqual("username", devtest_identity["os_username"])
        self.assertEqual("password", devtest_identity["os_password"])
        self.assertEqual("tenant", devtest_identity["os_tenant_name"])
        self.assertEqual("auth_url", devtest_identity["os_auth_url"])

    @mock.patch('mincer.marmite.os.environ', {})
    def test_identity_with_unknown_env_variables(self):
        devtest = self.marmite.environment("devtest")
        self.assertRaises(ValueError, devtest.identity)

    def test_identity_with_vavlues(self):
        devtest = self.marmite.environment("devtest")
        identity = devtest.tree["identity"]
        identity["os_auth_url"] = "auth_url"
        identity["os_username"] = "username"
        identity["os_password"] = "password"
        identity["os_tenant_name"] = "tenant"
        devtest_identity = devtest.identity()
        self.assertEqual("username", devtest_identity["os_username"])
        self.assertEqual("password", devtest_identity["os_password"])
        self.assertEqual("tenant", devtest_identity["os_tenant_name"])
        self.assertEqual("auth_url", devtest_identity["os_auth_url"])

    def test_application(self):
        self.assertEqual("wordpress", self.marmite.application().name())
        self.assertIsNotNone(self.marmite.application().medias())
        scenario = self.marmite.application().scenario()
        self.assertIsNotNone(scenario)
        for action in scenario:
            self.assertIsInstance(action, marmite.Action)

    def test_application_exception(self):
        del self.marmite.marmite_tree['application']["name"]
        self.assertRaises(marmite.NotFound, self.marmite.application().name)

    def test_action(self):
        scenario = self.marmite.application().scenario()
        self.assertIsNotNone(scenario)
        for action in scenario:
            self.assertIsInstance(action, marmite.Action)
            self.assertIsNotNone(action.driver())
            medias = action.medias()
            if medias != {}:
                for name in medias:
                    self.assertIsInstance(medias[name], media.Media)

    def test_action_exception(self):
        scenario = self.marmite.application().scenario()
        self.assertIsNotNone(scenario)
        for action in scenario:
            del action.tree["driver"]
            self.assertRaises(marmite.NotFound, action.driver)
            del action.tree["params"]
            self.assertRaises(marmite.NotFound, action.params)
