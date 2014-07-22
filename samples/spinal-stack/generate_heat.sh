#!/bin/bash

set -eux -o pipefail

TAG=${TAG:-"I1.0.0"}
DEPLOYMENT_YAML=${DEPLOYMENT_YAML:-"gitolite@git.labs.enovance.com:openstack-yaml-env-3nodes/deployment-heat-3nodes-D7.yml"}
DIST=${DIST:-"D7"}
RELEASE=${RELEASE:-"$DIST-I.1.1.0"}

[ -d "config-tools" ] || git clone https://github.com/enovance/config-tools



# 0) download.sh Fetch puppet, serverspec, eDeploy, etc and prepare a configuration
#    in the “top” directory, this including, /etc/hosts, eDeploy
#     arg1: tag
#     yaml: deployment yaml
#      *: key=val extra parameters
#
# deployment yaml has the following structure:
#
#  module:
#    git@github.com:enovance/puppet-openstack-cloud
#  serverspec:
#    git@github.com:enovance/openstack-serverspec.git
#  environment:
#    ci-redhat
#  infrastructure: (1)
#    git@github.com:enovance/openstack-yaml-infra-3nodes.git
#  jenkins:
#    git@github.com:enovance/jjb-openstack.git
#
# (1): a set of Jinja2 template file for:
#  ./hosts.tmpl
#  ./openrc.sh.tmpl
#  ./data/fqdn.yaml.tmpl
#  ./data/common.yaml.tmpl
#  ./data/type.yaml.tmpl
#  ./arch.yml.tmpl
#  ./heat.yaml.tmpl
#  ./example.yml
#  ./infra.yml
#
# the following step are done after that:
# 1) download.sh: compress the top directory in archive.tgz
# 2) send.sh: scp the tgz on the puppetmaster
# 3) extract-archive.sh: extracts the archive, still on the puppetmaster
# 4) extract-archive.sh: configure and launch Jenkins server
./config-tools/download.sh ${TAG} ${DEPLOYMENT_YAML} release=$RELEASE

(
    cd top/etc/config-tools/infra
    git checkout master
)

# NOTE(Gonéri)
# 10Gx12 → 120G. This is a bit to much for os-ci-test{6,7}
sed -i 's,volume_size: 10,volume_size: 5,'  top/etc/config-tools/global.yml

./config-tools/generate.py 0 top/etc/config-tools/global.yml top/etc/config-tools/infra/heat.yaml.tmpl > heat.yaml


echo "you can now call:"
echo "heat stack-create -f heat.yaml -P release=${RELEASE} -P dist=${DIST} robert-$RANDOM"
