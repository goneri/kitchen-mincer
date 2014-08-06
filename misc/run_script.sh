#!/bin/bash
rm -rf ${LOG_DIR}
mkdir ${LOG_DIR}
LOG_FILE=${LOG_DIR}/output.txt
exec > >(tee -a ${LOG_FILE}) 2>&1

set -eux -o pipefail

export PIP_DOWNLOAD_CACHE=/var/tmp/pip

CANONICAL="/tmp/${PROJECT}"
# test6: dev OpenStack
OS_ENV_TARGET="test6"
REPO=http://gerrit.sf.ring.enovance.com/r/${PROJECT}
VIRTUALENV_CACHE_TIME=10 # 10h

[ -d ${CANONICAL} ] || git clone ${REPO} ${CANONICAL}
cd ${CANONICAL}

git reset --hard
git clean -ffdx -e .tox
if [ -n ${REF_ID:-""} ]; then
    # This is Jenkins, we use our beloved realm to do the grunt work
    OS_ENV_TARGET="test7"
    REVISION_ID=${REF_ID##*/:-""}
    git fetch --all
    git fetch ${REPO} ${REF_ID}
    git checkout -B review/${AUTHOR%@*}/${CHANGE_ID}/${REVISION_ID} FETCH_HEAD
fi

git_clean_extra_args=""
# .tox chroot are here for more than 1 hour
if [ "$(find .tox -mtime +${VIRTUALENV_CACHE_TIME})" == "" ]; then
    git_clean_extra_args="-e .tox"
# .tox chroot are older than the *-requirements.txt files
elif [ "$(find .tox -cnewer test-requirements.txt -or -cnewer requirements.txt)" != "" ]; then
    git_clean_extra_args="-e .tox"
fi

# Cleaning the local git clone
git clean -ffdx ${git_clean_extra_args}

# Running tox, stop as soon as we get a failure
for i in pep8 py34 py27 validate-samples docs run_tests; do
    tox -e${i}
done

[[ -e ./cover ]] && mv cover ${LOG_DIR}/coverage
mv doc/build/html ${LOG_DIR}/docs
