#!/bin/bash
exec > >(tee -a ${LOG_FILE}) 2>&1


set -eux -o pipefail

export PIP_DOWNLOAD_CACHE=/var/tmp/pip

OS_ENV_TARGET=test7
TOX_TARGET=py27
REPO=http://gerrit.sf.ring.enovance.com/r/kitchen-mincer
REVISION_ID=${REF_ID##*/}
CANONICAL="/tmp/kitchen-mincer-${CHANGE_ID}-${REVISION_ID}"

function clean() {
    rm -rf ${CANONICAL}
}
trap clean EXIT

if [[ ! -d ${CANONICAL} ]];then
    git clone ${REPO} ${CANONICAL}
fi

cd ${CANONICAL}
git fetch ${REPO} ${REF_ID}
git checkout -B review/${AUTHOR%@*}/${CHANGE_ID}/${REVISION_ID} FETCH_HEAD

virtualenv .virtualenv
export PATH=.virtualenv/bin:$PATH
.virtualenv/bin/pip install -e.

./run_tests.sh ${OS_ENV_TARGET}
retcode=$?

exit ${retcode}
