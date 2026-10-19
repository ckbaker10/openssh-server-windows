#!/usr/bin/env python3
"""Assemble a Windows ZIP, verify PE imports, and retain corresponding sources."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work'
DIST = ROOT / 'dist'
NAME = 'openssh-10.6p1-cygwin-x86_64'
OBJDUMP = 'x86_64-pc-cygwin-objdump'
SYSTEM_DLLS = set('''advapi32 bcrypt cabinet cfgmgr32 comctl32 comdlg32 crypt32
    cryptbase dnsapi gdi32 iphlpapi kernel32 kernelbase mpr msvcrt ncrypt netapi32
    ntdll ole32 oleaut32 powrprof psapi rpcrt4 secur32 setupapi shell32 shlwapi
    user32 userenv version winmm winspool wintrust ws2_32 wtsapi32 normaliz
    ucrtbase authz winhttp wininet wldap32 dbghelp'''.split())


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalize(root):
    # Cygwin automatically maps /usr/bin and /usr/lib to /bin and /lib.
    for name in ['bin', 'lib']:
        source = root / 'usr' / name
        target = root / name
        if source.exists():
            shutil.copytree(source, target, symlinks=True, dirs_exist_ok=True)
            shutil.rmtree(source)


def resolve_link(path, root, seen=None):
    seen = set() if seen is None else seen
    if path in seen:
        raise RuntimeError(f'Symlink cycle: {path}')
    seen.add(path)
    if not path.is_symlink():
        return path
    target = os.readlink(path)
    logical = path
    for name in ['bin', 'lib']:
        if path.is_relative_to(root / name):
            logical = root / 'usr' / name / path.relative_to(root / name)
    candidate = root / target.lstrip('/') if target.startswith('/') else logical.parent / target
    candidate = Path(os.path.normpath(candidate))
    # Map Cygwin's automatic mount aliases when resolving archive links.
    for name in ['bin', 'lib']:
        prefix = root / 'usr' / name
        if candidate.is_relative_to(prefix):
            candidate = root / name / candidate.relative_to(prefix)
    if not candidate.is_relative_to(root):
        raise RuntimeError(f'Link outside package: {path}')
    return resolve_link(candidate, root, seen)


def materialize_links(root):
    # Windows ZIP extraction cannot reliably create POSIX symlinks. Copy their
    # in-package targets instead; unresolved optional data links are listed.
    links = [p for p in root.rglob('*') if p.is_symlink()]
    skipped = []
    for path in links:
        target = resolve_link(path, root)
        if not target.exists():
            skipped.append(str(path.relative_to(root)))
            path.unlink()
            continue
        path.unlink()
        if target.is_dir():
            shutil.copytree(target, path, symlinks=False)
        else:
            shutil.copy2(target, path)
            with target.open('rb') as stream:
                pe = stream.read(2) == b'MZ'
            if pe and path.suffix.lower() != '.exe':
                shutil.copy2(target, path.with_name(path.name + '.exe'))
    return skipped


def verify_pe(root):
    dlls = {p.name.lower() for p in (root / 'bin').glob('*.dll')}
    reports = {}
    missing = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(2) != b'MZ':
                continue
        output = subprocess.check_output([OBJDUMP, '-p', str(path)], text=True)
        if 'file format pei-x86-64' not in output:
            raise RuntimeError(f'Wrong PE architecture: {path}')
        imports = re.findall(r'DLL Name: (\S+)', output)
        reports[str(path.relative_to(root))] = imports
        for name in imports:
            lower = name.lower()
            siblings = {p.name.lower() for p in path.parent.glob('*.dll')}
            if lower in dlls or lower in siblings or lower.removesuffix('.dll') in SYSTEM_DLLS:
                continue
            if lower.startswith(('api-ms-win-', 'ext-ms-win-')):
                continue
            missing.append((str(path.relative_to(root)), name))
    if missing:
        raise RuntimeError(f'Unresolved DLL imports: {missing}')
    required = ['usr/sbin/sshd.exe', 'usr/sbin/sshd-session.exe',
                'usr/sbin/sshd-auth.exe', 'usr/sbin/sftp-server.exe',
                'bin/ssh-keygen.exe', 'bin/cygwin1.dll', 'bin/bash.exe',
                'bin/cygrunsrv.exe', 'bin/sh.exe', 'bin/awk.exe']
    for name in required:
        if not (root / name).is_file():
            raise RuntimeError(f'Missing required file: {name}')
    print(f'Verified {len(reports)} x86_64 PE files; all DLL imports resolve')
    return reports


def main():
    DIST.mkdir(exist_ok=True)
    output = WORK / NAME
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(WORK / 'runtime', output, symlinks=True)
    shutil.copytree(WORK / 'package', output, dirs_exist_ok=True, symlinks=True)
    normalize(output)
    skipped = materialize_links(output)
    for name in ['sshd_config', 'install-server.sh', 'install-server.cmd']:
        dest = output / ('etc/sshd_config' if name == 'sshd_config' else name)
        shutil.copy2(ROOT / 'packaging' / name, dest)
    # Batch files need CRLF when extracted by ordinary Windows ZIP tools.
    batch = output / 'install-server.cmd'
    batch.write_bytes(batch.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    for directory in ['var/empty', 'var/log', 'var/run', 'home', 'tmp']:
        (output / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'docs' / 'windows-installation.md', output / 'INSTALLATION.md')
    reports = verify_pe(output)
    lock = json.loads((ROOT / 'build' / 'inputs.lock.json').read_text())
    manifest = {
        'openssh': lock['openssh'], 'cygwin': lock['cygwin'],
        'compiler': subprocess.check_output(['x86_64-pc-cygwin-gcc', '--version'], text=True).splitlines()[0],
        'binutils': subprocess.check_output([OBJDUMP, '--version'], text=True).splitlines()[0],
        'compiler_sha256': sha256(Path(shutil.which('x86_64-pc-cygwin-gcc'))),
        'source_date_epoch': int(os.environ.get('SOURCE_DATE_EPOCH', '1791244800')),
        'builder_image_id': (WORK / 'builder-image-id.txt').read_text().strip(),
        'rpms': sorted(subprocess.check_output(['rpm', '-qa'], text=True).splitlines()),
        'configure': (WORK / 'obj' / 'config.status').read_text().split('ac_cs_config=')[1].splitlines()[0],
        'inputs': json.loads((WORK / 'download-manifest.json').read_text()),
        'pe_imports': reports, 'omitted_optional_links': skipped,
        'file_sha256': {str(p.relative_to(output)): sha256(p)
                        for p in sorted(output.rglob('*')) if p.is_file()},
    }
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(ROOT / 'build' / 'inputs.lock.json', output / 'inputs.lock.json')
    # Keep the signed index and signature next to the exact source archives.
    sources = DIST / (NAME + '-sources.tar')
    with tarfile.open(sources, 'w') as archive:
        source_paths = {p['source'] for p in lock['packages'].values() if p.get('source')}
        source_paths.add(lock['openssh_source'])
        for name in sorted(source_paths):
            archive.add(WORK / 'downloads' / name, arcname=name)
        archive.add(ROOT / 'build' / 'inputs.lock.json', arcname='inputs.lock.json')
        for path in sorted((WORK / 'metadata').glob('*')):
            archive.add(path, arcname='metadata/' + path.name)
        archive.add(ROOT / 'patches', arcname='patches')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '1791244800'))
    with zipfile.ZipFile(DIST / (NAME + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(NAME + '/' + str(path.relative_to(output)), time.gmtime(epoch)[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
                archive.writestr(info, path.read_bytes())
    artifacts = [DIST / (NAME + '.zip'), sources]
    (DIST / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in artifacts))
    for path in artifacts:
        print(f'{path}: {path.stat().st_size} bytes; SHA-256 {sha256(path)}')


if __name__ == '__main__':
    main()
