"""Encrypted WinRM transport for disposable Windows acceptance guests.

OPENSSH_TEST_ROOT holds private config.json and client/server credentials.json.
Never use this runner against a production machine.
"""
import base64
import atexit
import json
import os
from pathlib import Path
import sys
import winrm

ROOT = Path(os.environ.get('OPENSSH_TEST_ROOT', 'work/windows-lab')).resolve()
CONFIG = json.loads((ROOT / 'config.json').read_text())
_sessions = {}
_shells = {}


def render(text):
    values = {
        'MACHINE': CONFIG['client_name'],
        'DOMAIN-DC': CONFIG['server_name'],
        'DOMAIN': CONFIG['domain_netbios'],
        'SOURCE_CIDR': CONFIG['source_cidr'],
        'SOURCE_ADDRESS': CONFIG['source_address'],
        'DENIED_SOURCE': CONFIG['denied_source'],
        'DOMAIN_DNS': CONFIG['domain_dns'],
        'DOMAIN_ADMIN_NAME': CONFIG.get('domain_admin_name', 'Administrator'),
        'DOMAIN_TEST_USER': CONFIG.get('domain_test_user', 'sshdomtest'),
        'SERVER_PRIVATE_ADDRESS': CONFIG.get('server_private_address', '192.0.2.20'),
        'CLIENT_PRIVATE_ADDRESS': CONFIG.get('client_private_address', '192.0.2.21'),
        'ARCHIVE_URL': CONFIG['archive_url'],
        'CANDIDATE_SHA256': CONFIG.get('candidate_sha256', 'NOT_CONFIGURED'),
    }
    for token, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(token, value)
    return text


def session(machine):
    if machine not in ('client', 'server'):
        raise ValueError('Unknown guest')
    if machine not in _sessions:
        path = ROOT / machine / 'credentials.json'
        if path.stat().st_mode & 0o077:
            raise ValueError('Credential file must have mode 0600')
        account = json.loads(path.read_text())
        _sessions[machine] = winrm.Session(
            CONFIG[machine + '_url'], auth=(account['username'], account['password']),
            transport='ntlm', message_encryption='auto',
            ca_trust_path=str(ROOT / CONFIG[machine+'_ca']) if CONFIG.get(machine+'_ca') else None,
            server_cert_validation='validate',
            operation_timeout_sec=60, read_timeout_sec=75)
    return _sessions[machine]


def ps(machine, script, payload=b''):
    current = session(machine)
    script = render(script)
    # Stream scripts as well as data: nested test scripts can exceed cmd.exe's
    # command-line limit. Credentials remain in encrypted stdin, never argv.
    loader = ("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';try{"
              "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
              "$e=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
              "[Console]::SetIn([IO.StringReader]::new([Text.Encoding]::UTF8.GetString("
              "[Convert]::FromBase64String($e.input))));&([ScriptBlock]::Create($e.script));"
              "if(-not $?){exit 1}}catch{Write-Error -ErrorRecord $_ -ErrorAction Continue;exit 1}")
    encoded = base64.b64encode(loader.encode('utf-16-le')).decode('ascii')
    envelope = json.dumps({'script': script, 'input': base64.b64encode(payload).decode('ascii')}).encode()
    if len(envelope) > 65536:
        raise ValueError('Input exceeds one bounded WinRM message')
    protocol = current.protocol
    if machine not in _shells:
        # CIM/COM providers can outlive an individual PowerShell process.
        # Hold its user hive for the complete controller run instead of
        # unloading it between commands and leaving stale registry handles.
        _shells[machine] = protocol.open_shell(
            noprofile=os.environ.get('OPENSSH_TEST_NO_PROFILE')=='1', codepage=65001)
    shell = _shells[machine]
    command = None
    try:
        command = protocol.run_command(shell, 'powershell.exe',
            ['-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            console_mode_stdin=False, skip_cmd_shell=True)
        protocol.send_command_input(shell, command, envelope, end=True)
        return winrm.Response(protocol.get_command_output(shell, command))
    finally:
        if command is not None:
            protocol.cleanup_command(shell, command)


def close_shells():
    for machine, shell in list(_shells.items()):
        try:
            _sessions[machine].protocol.close_shell(shell)
        except Exception as error:
            print('WinRM shell cleanup: '+type(error).__name__,file=sys.stderr)
    _shells.clear()


atexit.register(close_shells)


if __name__ == '__main__':
    try:
        result = ps(sys.argv[1], Path(sys.argv[2]).read_text())
        sys.stdout.buffer.write(result.std_out)
        sys.stderr.buffer.write(result.std_err)
        sys.exit(result.status_code)
    except Exception as error:
        print('Windows request failed: ' + type(error).__name__, file=sys.stderr)
        sys.exit(2)
