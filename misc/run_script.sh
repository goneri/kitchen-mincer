#!/bin/bash
exec > >(tee -a ${LOG_FILE}) 2>&1

set -eux -o pipefail

OS_ENV_TARGET=test7
TOX_TARGET=py27
REPO=http://gerrit.sf.ring.enovance.com/r/kitchen-mincer
CANONICAL="/tmp/kitchen-mincer-${CHANGE_ID}"

if [[ ! -d ${CANONICAL} ]];then
    git clone ${REPO} ${CANONICAL}
fi

cd ${CANONICAL}
git fetch ${REPO} ${REF_ID}
git checkout -B review/${AUTHOR%@*}/${CHANGE_ID}/${REF_ID##*/} FETCH_HEAD
virtualenv .virtualenv

source .virtualenv/bin/activate
.virtualenv/bin/pip install -e.
./run_tests.sh ${OS_ENV_TARGET}
retcode=$?

rm -rf ${CANONICAL}

exit ${retcode}
