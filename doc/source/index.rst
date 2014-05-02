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

    description: A wordpress in a container (web and DB)

    # an account on an OpenStack cloud providing Heat API.
    environments:
      devtest:
    # Implicite, heat is the default provider.
    #    provider: heat
        identity:
    #NOTE(Gonéri): Why the os_ prefix?
          os_auth_url: http://os-ci-test7.ring.enovance.com:5000/v2.0
          os_username: admin
          os_password: password
          os_tenant_name: demo
        medias:
          dump_mysql:
            type: dynamic
            sources:
              -
                type: script
                value: |
                    #!/bin/sh
                    echo this is my dump MySQL > dump.sql
                target: mysql
        key_pairs:
          stack_os_ci-test7: |
            ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCyiXfE1zHKdj6odbysr917Cn88ov0VQaPJtLKJyMNuRYAeMOFQHd50X8JO4dfZbmSo3YdJlVfz9FLRxE64mqj9bkN8hPFbkTG2F1AWXGPON5cmm4uiLPfQkWhX/LnClrhzZpNtMJYs5AEFeDs0POijcRugZsQA+wvLi0lSlhOfkqtjAJKpPUwy1wrJFDdvqdQBjpNQh/LB8c15XfQV2JT/3NX26dQe8zvHhL6NvfhBnAikodYkBr7UjSl36CBk0cPebZMZEBBiHdo76xORVkpmqDvkhFByXXeAsvRa2YWS4wxpiNJFswlRhjubGau7LrT113WMcPvgYXHYHf2IYJWD goneri.lebouder@enovance.com
        floating_ips:
          public_wordpress_ip: 172.24.4.3

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
      # params:
      #  image_id: Fedora-x86_64-20-20140407-sda.qcow
      medias:
        # A image content computed before the Heat creation
        wordpress_files:
            type: dynamic
            sources:
              -
                type: git
                value: https://github.com/WordPress/WordPress
                # The directory in the image where to store the files
                target: wordpress
                ref: 3.8.2
        fedora_dvd:
            type: block
            disk_format: iso
    #        copy_from: https://dl.fedoraproject.org/pub/fedora/linux/releases/20/Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso
            copy_from: http://clearos.mirrors.ovh.net/download.fedora.redhat.com/linux/releases/20/Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso
            checksum: 9a190c8b2bd382c2d046dbc855cd2f2b
        base_image:
            type: block
            disk_format: qcow2
            copy_from: http://download.fedoraproject.org/pub/fedora/linux/updates/20/Images/x86_64/Fedora-x86_64-20-20140407-sda.qcow2
            checksum: 1ec332a350e0a839f03c967c1c568623

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
	mediamanager -> media_1
	mediamanager -> media_2
    }
