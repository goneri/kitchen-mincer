#!/bin/bash
LOG_FILE=${LOG_DIR}/output.txt
exec > >(tee -a ${LOG_FILE}) 2>&1

set -eux -o pipefail

export PIP_DOWNLOAD_CACHE=/var/tmp/pip

OS_ENV_TARGET=test7
TOX_TARGET=py27
REPO=http://gerrit.sf.ring.enovance.com/r/${PROJECT}
REVISION_ID=${REF_ID##*/}
CANONICAL="/tmp/${PROJECT}-${CHANGE_ID}-${REVISION_ID}"

VIRTUALENV_CACHE_DIR=/var/tmp/${PROJECT}-venv
VIRTUALENV_CACHE_TIME=86400 # 1 day

function is_elapsed() {
   local filename=$1
   local changed=`stat -c %Y "$filename"`
   local now=`date +%s`
   local elapsed

   let elapsed=now-changed
   [[ ${elapsed} -gt ${VIRTUALENV_CACHE_TIME} ]] && return 0
   return 1
}

function clean() {
    # NOTE(chmou): This is for debugging
    [[ -e ${CANONICAL}/NOERASE ]] && return 0

    rm -rf ${CANONICAL}
}
trap clean EXIT


rm -rf ${CANONICAL}
git clone ${REPO} ${CANONICAL}

cd ${CANONICAL}
git fetch ${REPO} ${REF_ID}
git checkout -B review/${AUTHOR%@*}/${CHANGE_ID}/${REVISION_ID} FETCH_HEAD

export PATH=.virtualenv/bin:$PATH
virtualenv .virtualenv

if [[ -d  ${VIRTUALENV_CACHE_DIR} ]] && ! is_elapsed ${VIRTUALENV_CACHE_DIR}; then
   echo  "Using ${VIRTUALENV_CACHE_DIR}"

    # NOTE(chmou): Copying the full .virtualenv makes it for buggy path on the
    # bin/scripts of the old virtualenv path.
    # Using virtualenv-clone is supposed to do things properly but that doesn't work
    # Just copying lib is good enough for us since pip install would fix it
    # quickly for us.
    rm -rf .virtualenv/lib
    cp -a ${VIRTUALENV_CACHE_DIR}/lib .virtualenv/lib
   .virtualenv/bin/pip install -e. -r test-requirements.txt -r requirements.txt

    # Binaries that we need to use or that get messy
   .virtualenv/bin/pip install tox coverage --force --upgrade
else
   echo "Regenerating the virtualenv cache"
   .virtualenv/bin/pip install -e. -r test-requirements.txt -r requirements.txt
   .virtualenv/bin/pip install tox coverage --force --upgrade
   rm -rf ${VIRTUALENV_CACHE_DIR}
   cp -a .virtualenv ${VIRTUALENV_CACHE_DIR}
fi

retcode=0
[[ -e ./run_tests.sh ]] && {
    ./run_tests.sh ${OS_ENV_TARGET}
    retcode=$?
}

rm -rf ${LOG_DIR}/cover ${LOG_DIR}/diff-cover-report.html  ${LOG_DIR}/docs

.virtualenv/bin/pip install diff_cover
.virtualenv/bin/python setup.py testr --coverage --testr-args='{posargs}' --coverage-package-name=${REPO/kitchen-}
[[ -e .cover ]] && {
    .virtualenv/bin/coverage xml
    .virtualenv/bin/diff-cover coverage.xml --html-report ${LOG_DIR}/diff-cover-report.html
}

# Build docs
.virtualenv/bin/python setup.py build_sphinx
mv doc/build/html ${LOG_DIR}/docs

exit ${retcode}
