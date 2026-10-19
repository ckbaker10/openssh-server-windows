#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:$PATH"
if ! id -G | tr ' ' '\n' | grep -qx 544; then
    echo 'Run install-server.cmd from an elevated Administrator command prompt.' >&2
    exit 1
fi
mkdir -p /var/empty /var/log /var/run /tmp /home
chmod 1777 /tmp
chmod 755 /var/empty
chown SYSTEM /var/empty
chmod go-w / /bin /usr /usr/sbin /etc
exec /usr/bin/ssh-host-config "$@"
