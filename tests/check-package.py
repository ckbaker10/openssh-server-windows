#!/usr/bin/env python3
"""Verify the delivered ZIP, its checksums, PE imports and default policy."""

import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
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
    package.validate_windows_paths(n.rstrip('/') for n in archive.namelist())
    assert {n.split('/')[0] for n in archive.namelist()} == {package.ARCHIVE_ROOT}
    for name in ['tmp', 'var/empty', 'var/log', 'var/run', 'home']:
        assert package.ARCHIVE_ROOT + '/' + name + '/' in archive.namelist(), name
    archive.extractall(destination)
root = destination / package.ARCHIVE_ROOT
assert not (root / 'tests').exists()
assert not (root / 'TESTING.md').exists()
with tarfile.open(ROOT / 'dist' / (package.NAME + '-sources.tar')) as sources:
    names = set(sources.getnames())
    assert 'project/TESTING.md' in names
    expected_tests = {str(p.relative_to(ROOT)) for p in (ROOT / 'tests').rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts}
    assert {'project/' + n for n in expected_tests} <= names
    for path in package.project_source_files():
        name = 'project/' + str(path.relative_to(ROOT))
        assert name in names, name
        assert sources.extractfile(name).read() == path.read_bytes(), \
            'Source archive differs from the checked source: ' + name
manifest = json.loads((root / 'build-manifest.json').read_text())
assert manifest['openssh'] == '10.6p1'
assert manifest['cygwin'] == '3.6.12-1'
actual_files = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
assert actual_files == set(manifest['file_sha256']) | {'build-manifest.json'}, \
    'Archive file list does not match manifest'
for name, expected in manifest['file_sha256'].items():
    assert package.sha256(root / name) == expected, name
sums = {}
for line in (root / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    digest, name = line.split('  ', 1)
    assert name not in sums, name
    sums[name] = digest
assert sums == {n: d for n, d in manifest['file_sha256'].items() if n != 'SHA256SUMS'}
assert package.verify_pe(root) == manifest['pe_imports']
config = (root / 'etc' / 'sshd_config').read_text()
assert 'PasswordAuthentication no' in config
assert 'Subsystem sftp internal-sftp' in config
assert '# AllowUsers REPLACE_WITH_EXACT_CYGWIN_ACCOUNT' in config
assert '# AuthenticationMethods publickey' in config
assert not list(root.rglob('ssh_host_*_key'))
assert (root / 'bin' / 'ssh-host-config').is_file()
assert (root / 'lib' / 'terminfo' / '78' / 'xterm').is_file()
for name in ['sshd_config', 'ssh_config', 'nsswitch.conf']:
    assert (root / 'etc' / name).read_bytes() == (root / 'etc/defaults/etc' / name).read_bytes()
assert 'db_home: /home/%U' in (root / 'etc/nsswitch.conf').read_text()
helper = (root / 'bin/ssh-host-config').read_text()
assert '-D -E /var/log/sshd.log' in helper
assert 'Keeping existing $1' in helper
assert '/setowner' in helper and '*S-1-5-18' in helper
assert '-y tcpip' in helper
for name in ['install-server.sh', 'open-shell.sh', 'install-user.sh']:
    assert b'\r' not in (root / name).read_bytes()
for name in ['install-user.cmd', 'install-user.ps1', 'user-setup.psm1']:
    assert (root / name).is_file(), name
for name in ['INSTALLATION.md', 'NONADMIN-USERS.md', 'TROUBLESHOOTING.md', 'COMPILE.md']:
    assert (root / name).is_file(), name
assert b'\r\n' in (root / 'install-user.cmd').read_bytes()
print('ZIP CRC, Windows paths, no manuals, complete manifest, hashes, PE imports, configuration and key absence: PASS')
