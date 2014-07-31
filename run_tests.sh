#!/bin/bash

TARGET=${1:-test7}

set -ex
set -o pipefail

function test7 () {
    export OS_IDENTITY_API_VERSION=2.0
    export OS_PASSWORD=password
    export OS_AUTH_URL=http://10.151.68.51:5000/v2.0
    export OS_USERNAME=admin
    export OS_TENANT_NAME=demo
    export OS_VOLUME_API_VERSION=2
    export OS_NO_CACHE=1
}

function test6 () {
    export OS_IDENTITY_API_VERSION=2.0
    export OS_PASSWORD=password
    export OS_AUTH_URL=http://10.151.68.50:5000/v2.0
    export OS_USERNAME=admin
    export OS_TENANT_NAME=demo
    export OS_VOLUME_API_VERSION=2
    export OS_NO_CACHE=1
}


# we can be clever when it get complicated
if [[ ${TARGET} == "test6" ]];then
    test6
elif [[ ${TARGET} == "test7" ]];then
    test7
fi

kitchen-mincer --target devtest samples/jenkins
retcode=$?

# NOTE(chmou): Temporary until we figure out a better solution, for now we assume we own the host for CI
{ heat stack-list| awk '/COMPLETE|FAILED/ {print $4}' | xargs -r heat stack-delete ;} || true

exit $retcode
