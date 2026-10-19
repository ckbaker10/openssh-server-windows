#!/usr/bin/env bash
set -euo pipefail

parse_arguments() {
    service_name=openssh-cygwin
    helper_args=()
    show_help=no
    while (($#)); do
        case "$1" in
            --yes|-y|--no|-n) helper_args+=("$1"); shift ;;
            --name|-N)
                if [[ ! ${2-} =~ ^[A-Za-z0-9_.-]+$ ]]; then
                    echo 'Service name must contain only letters, numbers, _, . or -.' >&2
                    return 2
                fi
                service_name=$2
                shift 2 ;;
            --port|-p)
                if [[ ! ${2-} =~ ^[0-9]{1,5}$ ]] || ((10#${2:-0} < 1 || 10#${2:-0} > 65535)); then
                    echo 'Port must be an integer from 1 to 65535.' >&2
                    return 2
                fi
                helper_args+=(--port "$((10#$2))")
                shift 2 ;;
            --user|-u|--user=*|--pwd|-w|--pwd=*|--privileged)
                echo 'This package installs LocalSystem services only; service-account/password options are unsupported.' >&2
                return 2 ;;
            --help|-h) show_help=yes; shift ;;
            *) echo 'Unsupported installation option. Use --help.' >&2; return 2 ;;
        esac
    done
    helper_args+=(--name "$service_name")
}

prepare_owned_path() {
    local path=$1 mode=$2 system_directory windows_owner
    if ! chown "$(id -u):544" "$path" 2>/dev/null; then
        # Fix only our state paths, never the installation root or a user tree.
        system_directory="$(cygpath -u "${SYSTEMROOT:?Windows SYSTEMROOT is required}")/System32"
        windows_owner=$("$system_directory/whoami.exe")
        windows_owner=${windows_owner//$'\r'/}
        "$system_directory/icacls.exe" "$(cygpath -w "$path")" /setowner "$windows_owner" >/dev/null
        chown "$(id -u):544" "$path"
    fi
    chmod "$mode" "$path"
}

ensure_system_directory_acl() {
    # SYSTEM is represented as a group in the reported Cygwin ACLs.
    if ! setfacl -m g:18:rwx "$@"; then
        echo 'Warning: SYSTEM directory ACL could not be updated; check /var/log and /var/run access before starting the service.' >&2
    fi
    return 0
}

main() {
    parse_arguments "$@" || return $?
    if [[ $show_help == yes ]]; then
        echo 'Usage: install-server.cmd [--yes|--no] [--name NAME] [--port PORT]'
        echo 'Installs a LocalSystem service, preserves configuration, logs to /var/log/sshd.log.'
        return
    fi
    export PATH="/usr/bin:/bin:/usr/sbin:$PATH"
    if ! id -G | tr ' ' '\n' | grep -qx 544; then
        echo 'Run .\install-server.cmd from an elevated Administrator terminal.' >&2
        return 1
    fi
    if cygrunsrv -Q "$service_name" 2>/dev/null | grep -Eq 'Current State[[:space:]]*:[[:space:]]*Running'; then
        echo 'Stop the selected service before configuring it.' >&2
        return 1
    fi
    mkdir -p /var/empty /var/log /var/run /tmp /home /etc/backups
    prepare_owned_path /tmp 1777
    prepare_owned_path /var/empty 755
    prepare_owned_path /var/log 770
    prepare_owned_path /var/run 770
    ensure_system_directory_acl /var/log /var/run
    if [[ ! -e /var/log/sshd.log ]]; then
        : > /var/log/sshd.log
    fi
    prepare_owned_path /var/log/sshd.log 640
    local backup name
    backup=/etc/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$
    mkdir -m 700 "$backup"
    for name in sshd_config ssh_config nsswitch.conf; do
        if [[ -f /etc/$name ]]; then
            cp "/etc/$name" "$backup/$name"
            chmod 600 "$backup/$name"
        else
            cp "/etc/defaults/etc/$name" "/etc/$name"
        fi
    done
    echo "Configuration backup: $backup"
    echo 'Service account: LocalSystem. Existing services keep their registration; see upgrade instructions.'
    /usr/bin/ssh-host-config "${helper_args[@]}"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
