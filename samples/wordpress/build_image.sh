#!/bin/bash
#!/bin/bash
set -eu
set -o pipefail

export JENKINS_PLUGINS=git
export ELEMENTS_PATH=$PWD/../../elements:$PWD/repos/diskimage-builder/elements:$PWD/repos/heat-templates/hot/software-config/elements:$PWD/repos/tripleo-image-elements/elements
export PATH=$PWD/repos/diskimage-builder/bin:$PWD/repos/dib-utils/bin:$PATH

function prepare() {
    repos="diskimage-builder tripleo-image-elements
           heat-templates dib-utils"

    [ -d repos ] || mkdir repos
    (
        cd repos
        for repo in ${repos}; do
            [ -d ${repo} ] || git clone git://github.com/openstack/${repo}
        done
    )
}

if [ ! -f wordpress_image.qcow2 ]; then
    prepare
    ./repos/diskimage-builder/bin/disk-image-create -o wordpress_image \
        fedora \
        selinux-permissive \
        heat-cfntools \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
else
    echo "Wordpress image already exists"
fi
if [ ! -f mariadb_image.qcow2 ]; then
    prepare
    ./repos/diskimage-builder/bin/disk-image-create -o mariadb_image \
        fedora \
        selinux-permissive \
        heat-cfntools \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script
else
    echo "MariaDB image already exists"
fi
if [ ! -f base_image.qcow2 ]; then
    prepare
    ./repos/diskimage-builder/bin/disk-image-create -o base_image \
        fedora \
        selinux-permissive \
        heat-cfntools \
        os-apply-config \
        os-collect-config \
        vm \
        stackuser \
        heat-config \
        heat-config-script \
        serverspec
else
    echo "Base image already exists"
fi
