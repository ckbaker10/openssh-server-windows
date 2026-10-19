#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
started_epoch=$(date +%s)
mkdir -p work dist
image=localhost/openssh-server-windows-builder:10.6p1
python3 scripts/inputs.py fetch
podman build -f build/Containerfile -t "$image" .
podman image inspect "$image" --format '{{.Id}}' > work/builder-image-id.txt
podman run --rm --name openssh-server-windows-build \
    -v "$PWD:/project:Z" -e BUILD_JOBS="${BUILD_JOBS:-4}" \
    "$image" bash scripts/build-inside.sh
finished_epoch=$(date +%s)
printf 'Build completed in %s host seconds\n' "$((finished_epoch - started_epoch))"
