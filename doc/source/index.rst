..
    Copyright 2014 eNovance SAS <licensing@enovance.com>

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Introduction
============

Kitchen Mincer aims to answer the following needs:

- Give a way and tools to continously validate application deployment.
- Validate that my application still work even if I upgrade my OpenStack.

For the moment, it is not possible to deploy and test Openstack on
baremetal but we consider to deploy OpenStack on top of another OpenStack
for testing purposes.

Glossary
========

.. glossary::

    Application:

        * Heat template
        * Collection of medias (e.g: distribution repository)
        * Some tests

    Marmite:
        a test scenario

    Media:
        Some data needed to run the application, see `the medias`_ bellow:

        * ISO image retrieved from a HTTP location
        * An eDeploy image disk
        * Some files collected and aggregated (git repo, etc...)

    Provider:
        a driver for the cloud infrastructure we want to use

        * OpenStack with Heat (default)
        * In the future: Deployment on baremetal machines
        * Other...

    Configuration:
        The configuration is used to define:

        * how to access the OpenStack tenant
	* how to communicate with the server (Marmite)

    Mincer (the client):
        The tool that drive the test scenario.

    Kitchen Island:
        A internal code name, restricted to be kept internally and not communicated
	outside.

    Action:
        An action is one of the step of the scenario, like starting the infrastructure,
	running a ping, etc... Through the combination of several actions we can perform
	complex and customizable workflow.

    Scenario:
        A scenario is composed of a sequence of actions so that we can combine different
	actions to perform a deployment. For instance a scenario could be:

        * start infrastructure
        * init application
        * run tests
        * upgrade application
        * run tests

    Environment:
        Some platform specific informations.

Credentials
===========

Credentials can be stored in `~/.config/mincer/credentials.yaml`. If the file is missing,
the standard OpenStack environment variables will be loaded:

    * $OS_AUTH_URL
    * $OS_USERNAME
    * $OS_PASSWORD
    * $OS_TENANT_NAME

You can specify another location for your credentials with the `--credentials-file` parameters.

Marmite definition
==================

The Marmite describes the application, where it should be deployed and
validated. The Marmite is versioned on a git repository and the version
is the one corresponding to the last commit.

In the future, the version may be a more elaborated schema which would combine the
recent tag and current commit (i.e: the output of `git describe`) to
allow different releases channel (i.e: stable/testing/experimental).

marmite YAML file
-----------------

* environment
* application
    * name
    * scenario

The floating ips
----------------

Floating IP are depending on the environment. For example, an OpenStack tenant will get
its own list of reserved public IP. It may be important to reuse them when the application
will go live, for example, to preserve DNS or HA configuration.

The "floating_ips" section in the environment allows to specify some floating IPs which
are used by the Heat template. These floating IPs could be static or dynamic.

Example:

 .. code-block:: yaml
     :linenos:

        floating_ips:
          public_wordpress_ip: 172.24.4.1
          public_mysql_ip: 172.24.4.2
          my_apache_server: dynamic
          puppet_master: dynamic

If they are static then it should be pre-allocated in the environment. In the case of dynamic
floating IPs, the mincer will try to find a free one in the allocated pool if not it will
allocate a new one.

The medias
----------

The word media is used to describe all resources out of the Marmite.

For example:
    * A special operating system image available through HTTP
    * A snapshot of a Ceph volume
    * A database backup to restore stored in Swift
    * An Ansible configuration directory from a git repository

We fetch these external resources and create the corresponding images (eg. qcow2/raw files). Those medias
are then published as Glance images.

Glance must be provisioned before the stack startup because the associated Heat template
will depends on them.

These medias can be either:
    * In the application itself, e.g: a Fedora repository or an eDeploy image
    * In the environment, e.g: a backup to restore or some additional configuration.

.. autoclass:: mincer.media.Media
    :no-undoc-members:

The actions
-----------

The word action is used to describe all tasks we can perform in the environment.

For example:
    * Running a local command like a ping against a server
    * Starting the infrastructure
    * Running serverspec tests
    * etc...

Storage
-------

For each deployment on a CI the logs of the deployment would be stored
in a Swift storage server. Using a global admin account we store all
deployment results.

The path for the deployment ::

   /CLIENT_ID/ENVIRONMENT_NAME/MARMITE_COMMIT_ID/

In there we would store jenkins logs and other infos we can collect
about the current deployment.

Directory hierarchy
-------------------

Here is an example of the directory hierarchy of a product:

- wordpress
    - marmite.yaml
    - heat.yaml
    - build_image.sh
    - apt_mirror_config.sh
    - backup_wordpress.sql
    - db_install.sh
    - wp_install.sh

In addition to the marmite and heat files there is some shell scripts:

- build_image.sh is used to build the image needed by the Heat template.
- The other shell scripts are needed by Heat in order to configure the virtual machines.

Workflows
=========

Deployment
----------

1. Initialization
    1. Initialize the Mincer (aka Mixer)
    2. Load the marmite object
    3. Load the provider object
2. Prepare the provider if needed
3. Prepare external resources
    1. Get the media list from the marmite object
    2. Produce the associated images
    3. Upload the images in Glance and retrieve the image IDs
    4. Upload the keypairs

At this step we have the provider initialized and the IaaS provisioned so we
can run a scenario.

4. Load a scenario from the marmite object
    1. For each action in the scenario
        1. Run the action

An action can be as simple as runing a ping or deploying a complex stack which
do tasks.

The current available actions are:
    - start_infra:  run the stack for the infrastructure
    - local_script: run a local command
    - simple_check: ru a command (example: ping) from an ephemeral stack
    - serverspec_check:  running serverspec tests

5. Retrieve and store the logs through the use of the log dispatcher

Each actions write its logs in stdout so that we can easily retrieve it.


Functional testing
------------------

We deploy applications through the use of Heat templates [#other_cloud]_. Once the
application is deployed we can start to run some tests campaign (unit tests,
functional tests, etc…).

Depending on the needs, tests can be very different:

A. A couple of pings from the mincer machine
B. A complex test scenario written in Python
C. A benchmark depending on a large number of virtual machines

That's the reason why they are based on *drivers*.

*SimpleCheck*
    This driver relies on command return code. It's similar to what is commonly
    done in the monitoring world. For example: call ping 5 time against all the
    host.

This is an example of a test used to run benchmark against a Wordpress
instance (Solution B).

.. blockdiag::

    blockdiag admin {

        group clusterA {
	    label = "WORDPRESS"
            shape = line
            style = dashed

	    floatingIP

	    "VM Apache";
	    "VM MySQL";
            "floatingIP";
	}

        group clusterB {
            label = "ACTION: TESTER STACK"
            color = red
            shape = line
            style = dashed

	    "VM test 1"
	    "VM test 2"
	    "VM test 3"
	}
	"floatingIP" -- "VM Apache"
	"VM MySQL" -- "VM Apache"
	"VM test 1" -- "floatingIP"
        "VM test 2" -- "floatingIP"
	"VM test 3" -- "VM MySQL"
   }



.. toctree::
    workflow
    api/modules


.. rubric:: Footnotes

.. [#other_cloud] At this time, we only focus on getting the OpenStack Heat provider working.
   We are planning to provide another provider in the near future to support
   `eDeploy <https://github.com/enovance/edeploy>`_.
