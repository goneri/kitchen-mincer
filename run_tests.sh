#!/bin/bash

set -ex
set -o pipefail

exec kitchen-mincer --target devtest samples/jenkins
