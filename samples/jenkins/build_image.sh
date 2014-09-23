#!/bin/bash

set -eu
set -o pipefail

export JENKINS_PLUGINS=git

[ -d repos ] || mkdir repos
[ -d repos/diskimage-builder ] || git clone https://github.com/openstack/diskimage-builder.git repos/diskimage-builder
[ -d repos/tripleo-image-elements ] || git clone https://git.openstack.org/openstack/tripleo-image-elements.git repos/tripleo-image-elements
[ -d repos/heat-templates ] || git clone git://git.openstack.org/openstack/heat-templates repos/heat-templates

export ELEMENTS_PATH=$PWD/elements:$PWD/repos/diskimage-builder/elements:$PWD/repos/heat-templates/hot/software-config/elements:$PWD/repos/tripleo-image-elements/elements

if [ ! -f jenkins_image.qcow2 ]; then
    ./repos/diskimage-builder/bin/disk-image-create -o jenkins_image \
        fedora \
        jenkins \
        heat-cfntools \
        jenkins-jjb \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
else
    echo "Jenkins image already exists"
fi
if [ ! -f base_image.qcow2 ]; then
    ./repos/diskimage-builder/bin/disk-image-create -o base_image \
        fedora \
        heat-cfntools \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
else
    echo "Base image already exists"
fi
