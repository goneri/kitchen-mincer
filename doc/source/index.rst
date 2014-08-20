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

    Marmite: an application and environments

        * An application
        * Environments (reference or in-line)

    Environment:

        * An account of an OpenStack providing Heat API. A name can be
          specified to describe the environment like (testing, prod, staging, etc..)
        * Collection of medias (e.g: Application backup to restore)

    Media:

        Some data needed to run the application, see `the medias`_ bellow:

        * ISO image retrieved from a HTTP location
        * An eDeploy image disk
        * Some files collected and aggregated (git repo, etc...)

    Provider: a driver for the cloud infrastructure we want to use

        * OpenStack with Heat (default)
        * In the future: Deployment on baremetal machines
        * Other...

    Credentials:
        A set of credentials for the provider.

    Mincer:
        The tool in charge of the initial deployment of the infrastructure.

    Kitchen Island:
        A internal code name, restricted to be kept internally and not communicated outside.

    Action:
        An action is a specific kind of task, like starting the infrastructure, running a ping, etc... Through
        the combination of several actions we can perform complex and customizable workflow.

    Scenario:
        A scenario is composed of a sequence of actions so that we can combine different actions to perform
        a complex deployment.
        For instance a scenario could be:

            - start infrastructure
            - init application
            - run tests
            - upgrade application
            - run tests

    logdispatcher:
        The log dispatcher is the object in charge of distributing the logs on different targets, it could be
        an Object storage, or a local directory. Thanks to the driver mechanism we can easily add new backends.

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

* environments
    * <env name 1>
        * medias
        * key_pairs
        * floating_ips
        * logdispatchers
    * <env name 2>
        * ...
* application
    * name
    * medias
    * scenario

The floating ips
----------------

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
    * In the environment, e.g: a backup to restore or some additional configuration

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
B. The use of an external tool like `serverspec`
C. A complex test scenario written in Python
D. A benchmark depending on a large number of virtual machines

That's the reason why they are based on *drivers*.

*SimpleCheck*
    This driver relies on command return code. It's similar to what is commonly
    done in the monitoring world. For example: call ping 5 time against all the
    host.
*ServerSpec*
    Call *serverspec* ( http://serverspec.org/ ) command.

Rational regarding the use of an ephemeral stack to run actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This paragraph explains the reasons why we added the ability to run ephemeral stacks
for some actions that run the tests.

If we run the tests directly from the machine that run the mincer:

    The most obvious and easy way to run the tests is to do it directly from the
    mincer just after the deployment of the application.

    The drawbacks of that solution are:

    - The Mincer will not scale very well because the server have limited resources.
      For instance, it will be hard to stress the application with 100k+
      connections.
    - Test results depends on the Mincer host machine configuration, so it will be
      hard to reproduce some tests which is business strategic in our context.
    - We cannot directly access the internal IP within the tenant

If we run the tests from a temporary Heat stack:

    The idea in this solution is to consider a test as an application which
    tests another one. The same way the Mincer creates application stacks, it
    also creates temporary Heat stack used to run the tests.

    These ephemeral stacks are designed to run tasks against an
    application.
    By using this solution, we can leverage Heat to express complex tests
    scenarios and then we do not add complexity in the Mincer.

    They are very similar to an application:

    - same YAML structure
    - with optional media and ssh key structure
    - a heat.yaml file

    But they are also different:

    - limited lifetime (ephemeral stacks)
    - hard drive are volatile
    - are in a *test* section of the marmite

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

.. [#other_cloud] For the moment, we only work with OpenStack Heat. The support of
   other cloud technologies is a mid-term goal.
