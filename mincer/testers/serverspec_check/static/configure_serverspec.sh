#!/bin/bash -v

set -eux
set -o pipefail

export HOME=/root
touch $HOME/.rspec
echo -e $test_private_key >> /root/.ssh/id_rsa

chmod 600 /root/.ssh/id_rsa

mount /dev/vdb1 /srv

cd /srv/data/serverspec
mv /srv/data/serverspec/spec/target /srv/data/serverspec/spec/${target}

SERVERSPEC_USER="stack" rake spec | sed "1 d"

