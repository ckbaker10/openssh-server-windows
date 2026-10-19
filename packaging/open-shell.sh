#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:$PATH"
entry=$(getent passwd "$(id -u)")
IFS=: read -r _account _password _uid _gid _comment HOME _shell <<< "$entry"
if [[ $HOME != /* ]]; then
    echo 'Cannot resolve an absolute home directory from the Cygwin account database.' >&2
    exit 1
fi
export HOME
if [[ -d $HOME ]]; then
    cd "$HOME"
fi
exec /bin/bash --noprofile --norc "$@"
