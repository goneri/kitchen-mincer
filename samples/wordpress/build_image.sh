#!/bin/bash

set -eu
set -o pipefail

[ -d repos ] || mkdir repos
[ -d repos/diskimage-builder ] || git clone https://github.com/openstack/diskimage-builder.git repos/diskimage-builder
[ -d repos/tripleo-image-elements ] || git clone https://git.openstack.org/openstack/tripleo-image-elements.git repos/tripleo-image-elements
[ -d repos/heat-templates ] || git clone git://git.openstack.org/openstack/heat-templates repos/heat-templates

export ELEMENTS_PATH=$PWD/repos/diskimage-builder/elements:$PWD/repos/heat-templates/hot/software-config/elements:$PWD/repos/tripleo-image-elements/elements
./repos/diskimage-builder/bin/disk-image-create -o base_image \
    ubuntu \
    heat-cfntools \
    os-apply-config \
    os-collect-config \
    vm \
    stackuser \
    heat-config \
    heat-config-script