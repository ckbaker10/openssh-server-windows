#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin

inspect_user() {
    local name=$1
    [[ $name =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,19}$ ]] || return 2
    if id -G "$name" | tr ' ' '\n' | grep -qx 544; then
        echo 'Administrator accounts are not supported by install-user.' >&2
        return 2
    fi
    getent passwd "$name"
}

configure_user() {
    local name=$1 expected_uid=$2 entry uid user_home path mode
    entry=$(inspect_user "$name")
    IFS=: read -r _account _password uid _gid _comment user_home _shell <<< "$entry"
    [[ $uid == "$expected_uid" && $user_home == "/home/$name" ]] || return 2
    for path in "$user_home" "$user_home/.ssh" "$user_home/.ssh/authorized_keys"; do
        [[ ! -L $path ]] || { echo 'Symbolic links are not supported.' >&2; return 2; }
        [[ $(stat -c %u "$path") == "$expected_uid" ]] || return 2
    done
    chmod 600 "$user_home/.ssh/authorized_keys"
    chmod 700 "$user_home/.ssh" "$user_home"
    for path in "$user_home" "$user_home/.ssh" "$user_home/.ssh/authorized_keys"; do
        mode=700
        [[ $path != */authorized_keys ]] || mode=600
        [[ $(stat -c %a "$path") == "$mode" ]] || return 2
    done
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    case ${1-} in
        inspect) [[ $# == 2 ]] && inspect_user "$2" ;;
        configure) [[ $# == 3 ]] && configure_user "$2" "$3" ;;
        *) echo 'Use install-user.cmd NAME PUBLIC_KEY_FILE from an elevated terminal.' >&2; exit 2 ;;
    esac
fi
