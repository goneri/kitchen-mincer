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

Glossary
========

.. glossary::

    Application:
        * Heat file + Heat components
        * Collection of medias (e.g: distribution repository)

    Marmitte: a application and environments
        * an application
        * collection of medias (e.g: Application backup to restore)
        * environnement (reference or in-line)

    Environnement:
        an account of an OpenStack cloud providing Heat API.

    Media:
        a file or VCS repository used by applications, the medias may be aggregated in a disk
        image. See `the medias`_ bellow.

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

Marmite definition
==================

The medias
----------

The word media is used to describe all resources out of the Marmitte. For example:

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


marmite YAML file
-----------------

.. code:: yaml

    description: A wordpress in a container (web and DB)

    # an account on an OpenStack cloud providing Heat API.
    environments:
      devtest:
        # The nature of the env, for example here it is based on Heat+Docker
        provider: heat-devstack-docker
        provider_params:
          image: heat-devstack-docker
          flavor: m1.medium
          keypair: Nopasswd
          ip: 46.231.128.152
        # Credentials required to connect to the OpenStack
        identity:
          os_username: $OS_USERNAME
          os_tenant_name: $OS_TENANT_NAME
          os_password: $OS_PASSWORD
          os_auth_url: $OS_AUTH_URL
        # A list of floating IP dedicated to the kitchen.
        # /!\ this list is associated with the OS_TENANT_NAME /!\
        ip_pool:
          - 10.0.0.4
          - 10.0.0.5
          - 10.0.0.6
      # Another environnement
      os-ci-test6:
    # Implicite, heat is the default provider.
    #    provider: heat
        identity:
          os_username: bob_l_eponge
          os_tenant_name: $OS_TENANT_NAME
          os_password: $OS_PASSWORD
          os_auth_url: $OS_AUTH_URL
        ip_pool:
          - 46.231.128.152
          - 46.231.128.153

    application:
      # Name of the application, Stack will be called according to this name
      name: wordpress

      # By convention, the heat file will be located here:
      # <root>/applications/<name e.g: wordpress>/heat.yaml

      # Arguments for the heat command (-P), depending on the type, some value may be
      # generated:
      #  - floating_ip: get an IP from the pool depending on its position
      #  - keypair: retrieve a key content from a keys/<name>.pub
      #  - media: returns the image id of the media in Glance
      params:
        - { type: floating_ip, name: mysql_server,  idx: 0 } // TODO
        - { type: floating_ip, name: http_server,  idx: 1 }
        # the keypair(s) to use, keypair name is the filename without the extension,
        # e.g: keys/roberto.pub → roberto
        - { type: keypair, name: roberto_key }
        - { type: value, name: blog_title, value: I'm sexy and I know it! }
        - { type: media, name: wp_files }
        - { type: media, name: sql_db_dump  }
      medias:
        # An image content computed before the Heat creation wp_files:
          type: git
          value: https://github.com/WordPress/WordPress
          # The directory in the image where to store the files
          target: ironic
          ref: 3.8.2
        sql_db_dump:
          type: script
          value: |
                  #!/bin/sh
                  mysqldump -hdbprod -utoto -ptoto wordpress > wordpress_prod.sql
          target: db

Directory hierarchy
-------------------

- marmite.yaml
- heat.yaml
- environments/
    * devtest.yaml
    * prod.yaml
- keys/
    * roberto.pub
    * kitty.pub

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
    2. get the media list from the marmitte object
    3. fetch the media and produce the associated images
    4. upload the images in Glance and retrieve the image IDs
    5. Upload the keypairs
4. Compute the heat arguments (get image_id from MediaManager)
5. Call Heat with the arguments
6. Wait for stack being ready

Functional test
---------------

.. todo::

Sprint 4 -- Investigate the different method of testing, properly categorize them of what we want to do

Code architecture
=================

- The entry point of the application is the Main class.
- The Mincer class instantiates the Marmite object and load the provider specified
  in the marmite.yaml file.
- The MediaManager is in charge of collecting the medias from the marmitte and
  provisioning each images with the corresponding application code afterwards it
  push them as images in Glance.
- The Provider instantiates the MediaManager and start to deploy the application.


.. graphviz::

    digraph G {

        node [
        fontname = "Bitstream Vera Sans"
        fontsize = 8
        shape = "record"
        ]

        edge [
        arrowtail = "empty"
        ]

	interface [ shape = "parallelogram"  ]

        main -> mincer
        mincer -> marmite
	mincer -> interface
	mincer -> environment
	interface -> provider
	mincer -> mediamanager
    }
