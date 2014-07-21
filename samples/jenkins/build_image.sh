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

(
    cd repos/heat-templates
    curl 'https://review.openstack.org/changes/108330/revisions/4940c653b1735bac59b49697223c25ce699b3fce/patch?download'|base64 -d|patch -p1
)

export ELEMENTS_PATH=$PWD/elements:$PWD/repos/diskimage-builder/elements:$PWD/repos/heat-templates/hot/software-config/elements:$PWD/repos/tripleo-image-elements/elements
./repos/diskimage-builder/bin/disk-image-create -o jenkins_debian \
    debian-systemd \
    jenkins-jjb \
    kitchen-mincer \
    os-apply-config \
    os-collect-config \
    vm \
    stackuser \
    heat-config \
    heat-config-script
