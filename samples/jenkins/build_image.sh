#!/bin/bash

set -eu
set -o pipefail

export DIB_DEBIAN_USE_DEBOOTSTRAP_CACHE=1
export DIB_DISTRIBUTION_MIRROR=http://ftp2.fr.debian.org/debian
export DIB_RELEASE=wheezy
export JENKINS_PLUGINS=git

[ -d repos ] || mkdir repos
[ -d repos/diskimage-builder ] || git clone https://github.com/openstack/diskimage-builder.git repos/diskimage-builder
[ -d repos/tripleo-image-elements ] || git clone https://git.openstack.org/openstack/tripleo-image-elements.git repos/tripleo-image-elements
[ -d repos/heat-templates ] || git clone git://git.openstack.org/openstack/heat-templates repos/heat-templates

export ELEMENTS_PATH=$PWD/elements:$PWD/repos/diskimage-builder/elements:$PWD/repos/heat-templates/hot/software-config/elements:$PWD/repos/tripleo-image-elements/elements

if [ ! -f jenkins_debian.qcow2 ]; then
    ./repos/diskimage-builder/bin/disk-image-create -o jenkins_debian \
        debian-systemd \
        heat-cfntools \
        jenkins-jjb \
        kitchen-mincer \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
fi
if [ ! -f base_image.qcow2 ]; then
    ./repos/diskimage-builder/bin/disk-image-create -o base_image \
        debian-systemd \
        heat-cfntools \
        kitchen-mincer \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
fi
