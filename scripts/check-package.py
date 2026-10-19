#!/usr/bin/env python3
"""Verify the delivered ZIP, its checksums, PE imports and default policy."""

import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package', ROOT / 'scripts' / 'package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)

for line in (ROOT / 'dist' / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert package.sha256(ROOT / 'dist' / name) == expected, name
destination = ROOT / 'work' / 'zip-check'
if destination.exists():
    shutil.rmtree(destination)
destination.mkdir()
with zipfile.ZipFile(ROOT / 'dist' / (package.NAME + '.zip')) as archive:
    assert archive.testzip() is None
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
    package.validate_windows_paths(archive.namelist())
    archive.extractall(destination)
root = destination / package.NAME
manifest = json.loads((root / 'build-manifest.json').read_text())
assert manifest['openssh'] == '10.6p1'
assert manifest['cygwin'] == '3.6.11-1'
actual_files = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
assert actual_files == set(manifest['file_sha256']) | {'build-manifest.json'}, \
    'Archive file list does not match manifest'
for name, expected in manifest['file_sha256'].items():
    assert package.sha256(root / name) == expected, name
assert package.verify_pe(root) == manifest['pe_imports']
config = (root / 'etc' / 'sshd_config').read_text()
assert 'PasswordAuthentication no' in config
assert 'Subsystem sftp internal-sftp' in config
assert not list(root.rglob('ssh_host_*_key'))
assert (root / 'bin' / 'ssh-host-config').is_file()
assert (root / 'lib' / 'terminfo' / '78' / 'xterm').is_file()
print('ZIP CRC, Windows paths, no manuals, complete manifest, hashes, PE imports, configuration and key absence: PASS')
