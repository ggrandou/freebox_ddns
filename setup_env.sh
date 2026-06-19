#!/bin/bash

srcname="${BASH_SOURCE[0]}"
dirname=$(dirname $srcname)

venvdir=$dirname/.venv

test -n "${BASH_SOURCE[1]}" || verbose=1

if [[ ! -d $venvdir ]] || [[ $srcname == "$0" ]]; then
    echo "setup virtual env $(realpath --relative-to=. $venvdir)"

    python3 -m venv $venvdir
    source $venvdir/bin/activate
    pip3 install --upgrade --editable "$dirname[dev]"
fi

if [[ $srcname == "$0" ]]; then
    # setup
    echo "now activate your virtual env with \"source $(realpath --relative-to=. $srcname)\""
elif [ "${BASH_SOURCE[1]}" ]; then
    # inside script
    source $venvdir/bin/activate
else
    # inside shell
    echo "activate virtual env"
    source $venvdir/bin/activate
    echo "type \"deactivate\" to exit the virtual env"
fi

ROOTDIR=$(realpath $dirname)

if ! [[ "$PATH" =~ "$ROOTDIR/tools:" ]]
then
    PATH="$ROOTDIR/tools:$PATH"
fi

export PATH
export ROOTDIR
