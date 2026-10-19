#!/usr/bin/env python3
"""Pin signed Cygwin inputs, download with hash checks, and stage packages."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import lzma
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work'
LOCK = ROOT / 'build' / 'inputs.lock.json'
MIRROR = 'https://mirrors.kernel.org/sourceware/cygwin/'
KEY = '56405CF6FCC81574682A5D561A698DE9E2E56300'
RUNTIME = ['cygwin', 'bash', 'coreutils', 'cygrunsrv', 'csih', 'diffutils',
           'sed', 'grep', 'gawk', 'getent', 'hostname', 'util-linux',
           'libssl3', 'zlib0', 'libcrypt2']
DEVEL = ['cygwin-devel', 'libssl-devel', 'zlib-devel', 'libcrypt-devel']


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.part')
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open('wb') as out:
        while block := response.read(1024 * 1024):
            out.write(block)
    tmp.replace(dest)


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def parse_index(text):
    packages = {}
    for section in text.split('\n@ ')[1:]:
        name, body = section.split('\n', 1)
        versions = []
        # A section starts with the current version; subsequent markers switch tracks.
        for part in re.split(r'\n\[(?:prev|test|curr)\]\n', body):
            fields = dict(re.findall(r'^(version|install|source|depends2): (.*)$', part, re.M))
            if 'version' in fields:
                versions.append(fields)
        packages[name] = versions
    return packages


def refresh():
    meta = WORK / 'metadata'
    meta.mkdir(parents=True, exist_ok=True)
    for name in ['setup.xz', 'setup.xz.sig']:
        download(MIRROR + 'x86_64/' + name, meta / name)
    download('https://cygwin.com/key/pubring.asc', meta / 'pubring.asc')
    key_info = subprocess.check_output(
        ['gpg', '--batch', '--show-keys', '--with-colons', str(meta / 'pubring.asc')],
        text=True)
    if f'fpr:::::::::{KEY}:' not in key_info:
        raise RuntimeError('Unexpected Cygwin signing key')
    subprocess.run(['gpg', '--batch', '--yes', '--dearmor', '--output',
                    str(meta / 'pubring.gpg'), str(meta / 'pubring.asc')], check=True)
    verification = subprocess.check_output(
        ['gpgv', '--status-fd', '1', '--keyring', str(meta / 'pubring.gpg'),
         str(meta / 'setup.xz.sig'), str(meta / 'setup.xz')], text=True)
    if f'[GNUPG:] VALIDSIG {KEY} ' not in verification:
        raise RuntimeError('Index was not signed by the pinned key')
    packages = parse_index(lzma.decompress((meta / 'setup.xz').read_bytes()).decode())
    runtime = set()

    def resolve(name):
        if name == '_windows' or name in runtime:
            return
        runtime.add(name)
        selected = packages[name][0]
        for dep in re.sub(r'\([^)]*\)', '', selected.get('depends2', '')).split(','):
            if dep.strip():
                resolve(dep.strip())

    for name in RUNTIME:
        resolve(name)
    selected = {}
    for name in sorted(runtime | set(DEVEL)):
        fields = packages[name][0]
        selected[name] = dict(fields, runtime=name in runtime)
    openssh = next(p for p in packages['openssh'] if p['version'] == '10.6p1-1')
    records = {}

    def record(spec):
        path, size, sha512 = spec.split()
        records[path] = {'path': path, 'size': int(size), 'sha512': sha512}
        return path

    for fields in selected.values():
        fields['install'] = record(fields['install'])
        if fields.get('source'):
            fields['source'] = record(fields['source'])
    source = record(openssh['source'])
    lock = {'openssh': '10.6p1', 'cygwin': selected['cygwin']['version'],
            'mirror': MIRROR, 'signing_key': KEY,
            'setup_sha256': digest(meta / 'setup.xz'),
            'openssh_source': source, 'packages': selected,
            'archives': sorted(records.values(), key=lambda x: x['path'])}
    LOCK.write_text(json.dumps(lock, indent=2) + '\n')
    print(f'Pinned {len(selected)} packages and {len(records)} archives to {LOCK}')


def fetch(lock):
    def one(record):
        path = WORK / 'downloads' / record['path']
        if not path.exists() or digest(path, 'sha512') != record['sha512']:
            download(lock['mirror'] + record['path'], path)
        if path.stat().st_size != record['size'] or digest(path, 'sha512') != record['sha512']:
            raise RuntimeError(f'Archive verification failed: {record["path"]}')
        return {**record, 'sha256': digest(path)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, lock['archives']))
    (WORK / 'download-manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'Verified {len(records)} downloads (SHA-512 and SHA-256)')


def extract(archive, destination):
    # External tar supports Cygwin's zstd archives on Python versions before 3.14.
    subprocess.run(['tar', '--extract', '--file', str(archive), '--directory',
                    str(destination), '--no-same-owner'], check=True)


def stage(lock):
    sysroot = WORK / 'sysroot'
    runtime = WORK / 'runtime'
    source = WORK / 'source-package'
    for path in [sysroot, runtime, source]:
        path.mkdir(parents=True, exist_ok=True)
    # Verify again so cached downloads cannot silently change between fetch and stage.
    for record in lock['archives']:
        if digest(WORK / 'downloads' / record['path'], 'sha512') != record['sha512']:
            raise RuntimeError(f'Changed archive: {record["path"]}')
    for fields in lock['packages'].values():
        archive = WORK / 'downloads' / fields['install']
        extract(archive, sysroot)
        if fields['runtime']:
            extract(archive, runtime)
    extract(WORK / 'downloads' / lock['openssh_source'], source)
    print('Staged current Cygwin sysroot, runtime, and OpenSSH source package')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['refresh-lock', 'fetch', 'stage'])
    args = parser.parse_args()
    WORK.mkdir(exist_ok=True)
    if args.command == 'refresh-lock':
        refresh()
    else:
        lock = json.loads(LOCK.read_text())
        {'fetch': fetch, 'stage': stage}[args.command](lock)


if __name__ == '__main__':
    main()
