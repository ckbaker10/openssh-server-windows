#!/usr/bin/env bash
set -euo pipefail
cd /project
package=/project/work/zip-check/openssh-10.6p1-cygwin-x86_64
export WINEPREFIX=/project/work/wineprefix-xvfb
export WINEARCH=win64 WINEDEBUG=-all
export WINEDLLOVERRIDES='mscoree,mshtml='
export DISPLAY=:99 XDG_RUNTIME_DIR=/tmp/openssh-wine-runtime
export WINEPATH='Z:\usr\lib64\wine-wow64\wine\x86_64-windows;Z:\project\work\zip-check\openssh-10.6p1-cygwin-x86_64\bin'
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
Xvfb "$DISPLAY" -screen 0 1024x768x24 > work/wine-xvfb.log 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
mkdir -p work/wine-smoke
mkdir -p "$package/var/empty" "$package/var/run" "$package/tmp"
# Wine loads its system DLLs directly from the Fedora installation. Updating an
# existing prefix through wineboot hangs in this rootless test environment.
timeout 120 wine "$package/bin/ssh.exe" -V
timeout 30 wine "$package/usr/sbin/sshd.exe" -V
timeout 30 wine "$package/bin/bash.exe" --noprofile --norc -c \
    'test -f /usr/sbin/sshd.exe && printf "Cygwin shell: PASS\n"'
if [[ ! -f work/wine-smoke/host_ed25519 ]]; then
    timeout 30 wine "$package/bin/ssh-keygen.exe" -q -t ed25519 -N '' \
        -f 'Z:\project\work\wine-smoke\host_ed25519'
fi
chmod 600 work/wine-smoke/host_ed25519
timeout 30 wine "$package/usr/sbin/sshd.exe" -t \
    -f /etc/sshd_config -h /cygdrive/z/project/work/wine-smoke/host_ed25519
echo 'Wine smoke tests: PASS (supplemental; native Windows acceptance is separate)'
