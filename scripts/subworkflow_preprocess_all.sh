#!/bin/bash
set -o nounset
set -o errexit
set -o pipefail

# dockstore_preprocess_all.sh [dockstore_preprocess.py] [WDL dir] [preprocess args]

preprocess=$1
dir=$2
shift 2;
args=$@

# preprocess all WDLs in the dir
for file in $dir*.wdl; do
    eval "python3 $preprocess --input-wdl-path $file $args";
done