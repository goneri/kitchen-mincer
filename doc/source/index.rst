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
- Validate that my application still work even if I upgrade my IAAS.

For the moment, it is not possible to deploy and test a IAAS on
baremetal.

Glossary
========

.. glossary::

    Application:
        * Heat file + Heat components
        * Collection of medias (e.g: distribution repository)

    Marmite: a application and environments
        * an application
        * collection of medias (e.g: Application backup to restore)
        * environnement (reference or in-line)

    Environnement:
        an account of an OpenStack cloud providing Heat API. A name
        can be specified to describe the environemnt like
        (testing/prod/staging etc..)

    Media:
        some data needed to run the application, see `the medias`_ bellow:
        * ISO image retrieved from a HTTP location
        * an eDeploy image disk
        * some files collected and aggregated (git, etc)

    Provider: a driver for the cloud infrastructure we want to use
        * OpenStack+Heat (default)
        * OpenStack+Docker+Heat
        * late

    Identity:
        a set of credentials for the provider

    Mincer:
        The tool in charge of the initial deployment of the infrastructure

    Kitchen Island:
        A internal code name, restricted to be kept internally and not communicated outside.

    Tester:
        A driver designed to run a specific kind of tests.

    Test:
        A process based on a `Tester` and designed to validate the good shape of a running Application.


Marmite definition
==================

The marmite describes the application, where it should be deployed and
validated. The marmite version is the current git commit. In the
future version may be a more elaborated schema which would combine the
recent tag and current commit (i.e: the output of `git describe`) to
allow different releases channel (i.e: stable/testing/experimental).

marmite YAML file
-----------------

* environments
    * identity
    * medias
    * key_pairs
* application
    * name
    * medias
    * garden gnome: the list of the associated tests
* testers
    * a_test_sample

The medias
----------

The word media is used to describe all resources out of the Marmite. For example:

* a special operating system image available through HTTP
* a snapshot of a Ceph volume
* a database backup to restore stored in Swift
* a Ansible configuration directory from a git repository

We fetch these external resources and push them in images. Those medias are published as
image.

They must be prepared and uploaded before the stack startup because Heat will need them.

These medias can be either:

* in the application itself, e.g: a Fedora repository or an eDeploy image
* in the user configuration, e.g: a backup to restore or some additional configuration

Storage
-------

For each deployment on a CI the logs of the deployment would be stored
in a Swift storage server. Using a global admin account we store all
deployments of a client.

The path for the deployment ::

   /CLIENT_ID/ENVIRONMENT_NAME/MARMITE_COMMIT_ID/

In there we would store jenkins logs and other infos we can collect
about the current deployment.

Syntax
~~~~~~


.. autoclass:: mincer.media.Media

Directory hierarchy
-------------------

At which stage in the development process, we keep the *environmenets*,
*applications* and *tests* section in the same file (*marmite.yaml*).

- marmite.yaml
- heat.yaml

Workflows
=========

Initial deployment
------------------

1. Step zero
    1. Initialize the Mincer (aka Mixer)
    2. load the Marmite
    3. load the Provider
2. Prepare the provider if needed (e.g: Docker)
3. Prepare media images (qcow2, raw)
    1. load the MediaManager object
    2. get the media list from the marmite object
    3. fetch the media and produce the associated images
    4. upload the images in Glance and retrieve the image IDs
    5. Upload the keypairs
4. Compute the heat arguments (get image_id from MediaManager)
5. Call Heat with the arguments
6. Wait for stack being ready
7. Process the tests against the newly created stack (See: `Functional testing`_)
    1. start an ephemeral stack in the same tenant
    2. run the test from that ephemeral stack
    3. collect the result
    4. destroy the stack
8. destroy the stack if needed

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
    This driver relys on command return code. It's similar to what is commonly
    done in the monitoring world. For example: call ping 5 time against all the
    host.
*ServerSpec*
    Call *serverspec* ( http://serverspec.org/ ) command.

Rational regarding the use of an ephemeral stack to run the test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This paragraph explains the reason why we decide to launch an ephemeral stack
to run the tests.


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
	    label = "my Wordpress (stack 1)"
	    floatingIP

	    "VM Apache";
	    "VM MySQL";
            "floatingIP";
	}

        group clusterB {
            label = "tester (stack 2)"
	    color=lightgrey
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
    code


.. rubric:: Footnotes

.. [#other_cloud] For the moment, we only work with OpenStack Heat. The support of
   other cloud technologies is a mid-term goal.
