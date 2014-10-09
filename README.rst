**************
Kitchen Mincer
**************

Seamless validate your application on complex infrastructure.

How to test the Kitchen Mincer
##############################

Requirements
************

You will need the following requirements:

* Python and some more packages
* An OpenStack Icehouse account with Heat enabled

You can install the dependencies with the following command on Fedora::

    sudo yum install python-pip gcc python-devel libffi-devel openssl-devel sudo

Additional dependencies are needed by the jenkins sample::

    sudo yum install git qemu-img


Run the Mincer from the source directory
****************************************

Install tox::

    pip install tox

Use tox to create a Python 2.7 virtualenv and run the test-suite::

    tox -epy27

Finally, launch the Mincer::

    PYTHONPATH=. .tox/py27/bin/python ./mincer/main.py --target devtest samples/jenkins

Install the Mincer
******************

Just use the common Python installation command::

    pip install .

You will then be able to call the `kitchen-mincer` command::

    kitchen-mincer --target devtest samples/jenkins

OpenStack tenant configuration
******************************

The Kitchen Mincer load the OpenStack credentials from your OS_* environment variables.
If you need to use some other configuration, you can create the `~/.config/mincer/credentials.yaml`
file.

For example:

.. code-block:: yaml

    os_auth_url: http://os-ci-test6.ring.enovance.com:5000/v2.0
    os_username: admin
    os_password: password
    os_tenant_name: demo


If you plan to use devstack, this is an example of the `local.conf` you can use to set up your OpenStack:

.. code-block::

    # -*- Mode: shell-script -*-
    [[local|localrc]]

    HOST_IP=10.151.68.51
    UNDO_REQUIREMENTS=false

    # Logs
    LOGFILE=/tmp/devstack.log
    SCREEN_LOGDIR=/tmp/screen-logs

    # Creds
    ADMIN_PASSWORD=password
    #KEYSTONE_TOKEN_FORMAT=UUID
    RABBIT_PASSWORD=8112166274b4f0198723
    DATABASE_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=7f00aa2752e42ff6eead
    SWIFT_HASH="robert"
    # Heat
    IMAGE_URLS+=",http://download.cirros-cloud.net/0.3.1/cirros-0.3.1-x86_64-disk.img"

    VOLUME_BACKING_FILE_SIZE="60G"
    SWIFT_LOOPBACK_DISK_SIZE="40G"

    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service neutron

    enable_service heat
    enable_service h-api
    enable_service h-eng
    enable_service h-api-cfn
    enable_service h-api-cw

    enable_service s-proxy
    enable_service s-object
    enable_service s-container
    enable_service s-account

    # Optional, to enable tempest configuration as part of devstack
    disable_service tempest


Documentation
#############

You can generate the documentation using the `tox` command::

    tox -edocs

The documentation will be generated in the `doc/build/html` directory.

Contact
#######

Please contact Team Boa <boa@enovance.com> if you have any questions.

