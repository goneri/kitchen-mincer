#!/bin/sh

set -eux

for dir in samples/*; do
    if [ -f $dir/marmite.yaml ]; then
        kitchen-mincer --test --target devtest --extra_params dist=foo --extra_params release=bar $dir
    fi
done
