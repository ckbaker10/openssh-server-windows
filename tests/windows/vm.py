"""Private KVM guests from immutable, already installed Windows checkpoints.

Does not download media, accept a license, install Windows or alter base guests.
Checkpoint folders need disk.qcow2, OVMF_VARS.fd, tpm/, credentials.json.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys


def qmp(directory, command, arguments=None):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(directory / 'qmp.sock'))
        stream = client.makefile('rwb', buffering=0)
        stream.readline()
        for request in ({'execute': 'qmp_capabilities'},
                        {'execute': command, 'arguments': arguments or {}}):
            stream.write(json.dumps(request).encode() + b'\n')
            while True:
                reply = json.loads(stream.readline())
                if 'error' in reply:
                    raise RuntimeError(reply['error']['desc'])
                if 'return' in reply:
                    break
        return reply['return']


def alive(path):
    if not path.exists():
        return False
    try:
        os.kill(int(path.read_text()), 0)
        return True
    except ProcessLookupError:
        return False


def clone(root, name, source):
    disk = source / 'disk.qcow2'
    if disk.stat().st_mode & 0o222:
        raise ValueError('The base checkpoint must be read-only')
    chain = json.loads(subprocess.check_output(
        ['qemu-img', 'info', '--backing-chain', '--output=json', str(disk)]))
    if len(chain) != 1 or chain[0]['format'] != 'qcow2':
        raise ValueError('Use a standalone immutable qcow2 checkpoint')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    directory = root / name
    directory.mkdir(mode=0o700)
    for filename in ('OVMF_VARS.fd', 'credentials.json'):
        shutil.copy2(source / filename, directory / filename)
    os.chmod(directory / 'credentials.json', 0o600)
    shutil.copytree(source / 'tpm', directory / 'tpm')
    subprocess.run(['qemu-img', 'create', '-q', '-f', 'qcow2', '-F', 'qcow2',
                    '-b', str(disk), str(directory / 'disk.qcow2')], check=True)
    print(name + ': private writable overlay created')


def run(root, name):
    directory = root / name
    if alive(directory / 'qemu.pid') or alive(directory / 'swtpm.pid'):
        raise ValueError('Guest or TPM already running')
    for filename in ('qemu.pid', 'tpm.sock', 'qmp.sock', 'vnc.sock'):
        (directory / filename).unlink(missing_ok=True)
    subprocess.run(['swtpm', 'socket', '--tpm2', '--tpmstate', 'dir='+str(directory/'tpm'),
                    '--ctrl', 'type=unixio,path='+str(directory/'tpm.sock'),
                    '--pid', 'file='+str(directory/'swtpm.pid'), '--daemon'], check=True)
    port = 56985 if name == 'client' else 56986
    args = ['qemu-system-x86_64', '-name', 'openssh-test-'+name,
            '-machine', 'q35,smm=on', '-accel', 'kvm', '-cpu', 'host', '-smp', '4', '-m', '8192',
            '-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.ms.fd',
            '-drive', 'if=pflash,format=raw,unit=1,file='+str(directory/'OVMF_VARS.fd'),
            '-global', 'driver=cfi.pflash01,property=secure,value=on',
            '-drive', 'file='+str(directory/'disk.qcow2')+',format=qcow2,if=ide',
            '-chardev', 'socket,id=chrtpm,path='+str(directory/'tpm.sock'),
            '-tpmdev', 'emulator,id=tpm0,chardev=chrtpm', '-device', 'tpm-tis,tpmdev=tpm0',
            '-netdev', 'user,id=nat,hostfwd=tcp:127.0.0.1:'+str(port)+'-:5985,hostfwd=tcp:127.0.0.1:'+str(port+1000)+'-:5986'+
                (',hostfwd=tcp:127.0.0.1:57222-:2222' if name == 'client' else ''),
            '-device', 'e1000e,netdev=nat,mac=52:54:00:aa:'+('10' if name=='server' else '20')+':01',
            '-netdev', 'socket,id=lab,'+('listen' if name=='server' else 'connect')+'=127.0.0.1:56990',
            '-device', 'e1000e,netdev=lab,mac=52:54:00:aa:'+('10' if name=='server' else '20')+':02',
            '-rtc', 'base=utc', '-vnc', 'unix:'+str(directory/'vnc.sock'),
            '-qmp', 'unix:'+str(directory/'qmp.sock')+',server=on,wait=off',
            '-pidfile', str(directory/'qemu.pid'), '-daemonize', '-D', str(directory/'qemu.log')]
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['clone', 'start', 'run', 'status', 'screen', 'powerdown', 'keys', 'https-forward'])
    parser.add_argument('machine', choices=['client', 'server'])
    parser.add_argument('--root', type=Path, default=Path('work/windows-lab'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--keys', default='ctrl+alt+delete')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == 'clone':
        if args.source is None:
            parser.error('clone requires --source CHECKPOINT_DIRECTORY')
        clone(root, args.machine, args.source.resolve())
    elif args.action == 'run':
        run(root, args.machine)
    elif args.action == 'start':
        unit = 'openssh-test-'+hashlib.sha256(str(root).encode()).hexdigest()[:8]+'-'+args.machine
        env = os.environ.copy()
        env.setdefault('XDG_RUNTIME_DIR', '/run/user/'+str(os.getuid()))
        env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path='+env['XDG_RUNTIME_DIR']+'/bus')
        subprocess.run(['systemd-run', '--user', '--unit='+unit, '--property=Type=oneshot',
                        '--property=RemainAfterExit=yes', sys.executable, str(Path(__file__).resolve()),
                        'run', args.machine, '--root', str(root)], env=env, check=True)
        print('Unit: '+unit+'.service')
    else:
        directory = root / args.machine
        if args.action == 'status':
            print(qmp(directory, 'query-status'))
        elif args.action == 'screen':
            path = directory / 'screen.ppm'
            qmp(directory, 'screendump', {'filename': str(path)})
            print(path)
        elif args.action == 'powerdown':
            qmp(directory, 'system_powerdown')
        elif args.action == 'https-forward':
            port=57985 if args.machine=='client' else 57986
            print(qmp(directory, 'human-monitor-command', {'command-line':'hostfwd_add nat tcp:127.0.0.1:'+str(port)+'-:5986'}))
        else:
            qmp(directory, 'send-key', {'keys': [{'type': 'qcode', 'data': key}
                                                for key in args.keys.split('+')]})


if __name__ == '__main__':
    main()
