"""Argument safeguards and the actual packaged configuration helper."""
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def bash(code):
    return subprocess.run(['bash', '-c', code], text=True, capture_output=True)


class InstallerArguments(unittest.TestCase):
    def parse(self, *args):
        return bash('source ' + shlex.quote(str(ROOT / 'packaging/install-server.sh'))
                    + '; parse_arguments ' + shlex.join(args)
                    + '; printf "%s\\n" "${helper_args[@]}"')

    def test_explicit_ports(self):
        for port in ('22', '2222', '65535', '00022'):
            result = self.parse('--yes', '--port', port)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--port\n' + str(int(port)) + '\n', result.stdout)

    def test_reject_invalid_options_without_echoing_secrets(self):
        for args in [('--pwd', 'secret-test-value'), ('--pwd=secret-test-value',),
                     ('--user', 'someone'), ('--privileged',),
                     ('--port', '0'), ('--port', '65536'), ('--port', '-1'),
                     ('--port',), ('--name', 'bad name'), ('--unknown',)]:
            result = self.parse(*args)
            self.assertEqual(result.returncode, 2, (args, result.stderr))
            self.assertNotIn('secret-test-value', result.stdout + result.stderr)

    def test_default_does_not_request_port_change(self):
        result = self.parse('--name', 'my-sshd')
        self.assertEqual(result.stdout.splitlines(), ['--name', 'my-sshd'])

    def test_system_group_acl_failure_is_reported_without_aborting(self):
        code = ('source ' + shlex.quote(str(ROOT / 'packaging/install-server.sh'))
                + '; setfacl() { printf "%s\\n" "$*"; return 1; }; '
                + 'ensure_system_directory_acl /var/log /var/run; echo continued')
        result = bash(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('-m g:18:rwx /var/log /var/run', result.stdout)
        self.assertIn('continued', result.stdout)
        self.assertIn('Warning:', result.stderr)

    def test_shell_replaces_inherited_home_from_account_lookup(self):
        # Isolate shell logic; actual Cygwin/Windows NSS needs native acceptance.
        code = ('getent() { printf "tester:x:1000:1000:Test:/tmp:/bin/bash\\n"; }; '
                'export -f getent; export HOME=/wrong-inherited-home; bash '
                + shlex.quote(str(ROOT / 'packaging/open-shell.sh'))
                + ' -c \'test "$HOME" = /tmp && test "$PWD" = /tmp\'')
        result = bash(code)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_startup_failures_and_helper_warnings_retain_owner_check(self):
        for existing, installed, helper_rc, startup_rc in [
                ('no', 0, 0, 0), ('no', 0, 0, 5), ('no', 0, 2, 0),
                ('no', 0, 2, 5), ('yes', 0, 0, 5), ('no', 1, 1, 0)]:
            with self.subTest(existing=existing, installed=installed,
                              helper=helper_rc, startup=startup_rc):
                code = ('source ' + shlex.quote(str(ROOT / 'packaging/install-server.sh'))
                        + '; service_name=test-sshd; '
                        + f'cygrunsrv() {{ return {installed}; }}; '
                        + f'configure_delayed_start() {{ echo startup; return {startup_rc}; }}; '
                        + f'finish_service_setup {existing} {helper_rc}')
                result = bash(code)
                changed = existing == 'no' and installed == 0
                self.assertEqual(result.returncode, helper_rc or (startup_rc if changed else 0))
                self.assertEqual('startup\n' in result.stdout, changed)
                self.assertIn('Get-Acl', result.stdout)
                if helper_rc:
                    self.assertIn(f'{helper_rc} errors/warnings', result.stderr)

    def test_sc_sets_delayed_start_only_for_selected_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'System32'
            directory.mkdir()
            sc = directory / 'sc.exe'
            sc.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\nexit 5\n')
            sc.chmod(0o755)
            code = ('source ' + shlex.quote(str(ROOT / 'packaging/install-server.sh'))
                    + '; export SYSTEMROOT=' + shlex.quote(tmp)
                    + '; cygpath() { printf "%s" "$2"; }; service_name=my-sshd; configure_delayed_start')
            result = bash(code)
            self.assertEqual(result.returncode, 5)
            self.assertEqual(result.stdout.splitlines(), ['config', 'my-sshd', 'start=', 'delayed-auto'])


class PackagedHelper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'work/zip-check/openssh-10.6p1-cygwin-x86_64/bin/ssh-host-config'
        if not path.exists():
            raise unittest.SkipTest('Run scripts/check-package.py first to test the delivered helper')
        cls.helper = path.read_text()

    def function(self, name):
        match = re.search(r'^' + name + r'\(\) \{\n.*?^\}[^\n]*', self.helper, re.M | re.S)
        self.assertIsNotNone(match, name)
        return match.group()

    def test_keeps_existing_config_and_installs_missing_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config'
            path.write_text('operator configuration\n')
            code = ('set -e; csih_inform() { :; }; '
                    'csih_install_config() { printf "default\\n" > "$1"; };\n'
                    + self.function('openssh_install_config') + '\n'
                    + 'openssh_install_config ' + shlex.quote(str(path)))
            self.assertEqual(bash(code).returncode, 0)
            self.assertEqual(path.read_text(), 'operator configuration\n')
            path.unlink()
            self.assertEqual(bash(code).returncode, 0)
            self.assertEqual(path.read_text(), 'default\n')

    def test_port_updates_include_default_and_missing_directive(self):
        for before in ('Port 2222\n', '#Port 22\n', 'PasswordAuthentication no\n'):
            for port in ('22', '2222'):
                with self.subTest(before=before, port=port), tempfile.TemporaryDirectory() as tmp:
                    config = Path(tmp) / 'sshd_config'
                    config.write_text(before)
                    code = ('csih_inform() { :; }; csih_warning() { echo "$*" >&2; }; '
                            + 'SYSCONFDIR=' + shlex.quote(tmp) + '; '
                            + 'strictmodes=yes; port_specified=yes; port_number=' + port + ';\n'
                            + self.function('sshd_config_tweak') + '\nsshd_config_tweak')
                    result = bash(code)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('Port ' + port, config.read_text().splitlines())

    def test_shell_syntax(self):
        result = subprocess.run(['bash', '-n'], input=self.helper, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_owner_change_skips_correct_owner_but_reports_real_failures(self):
        function = self.function('openssh_chown_service_file')
        for owner, chown_rc, fallback_rc, fallback_owner, expected_rc in [
                ('18', 1, 1, '1000', 0), ('1000', 0, 1, '1000', 0),
                ('1000', 1, 0, '18', 0), ('1000', 1, 5, '1000', 1),
                ('1000', 1, 0, '1000', 1)]:
            with self.subTest(owner=owner, chown=chown_rc, fallback=fallback_rc,
                              verified=fallback_owner), tempfile.TemporaryDirectory() as tmp:
                state = Path(tmp) / 'owner'
                state.write_text(owner)
                directory = Path(tmp) / 'System32'
                directory.mkdir()
                acl = directory / 'icacls.exe'
                acl.write_text('#!/bin/bash\nprintf "icacls:%s\\n" "$*"\n'
                               + f'echo {fallback_owner} > ' + shlex.quote(str(state))
                               + f'\nexit {fallback_rc}\n')
                acl.chmod(0o755)
                code = ('run_service_as=SYSTEM; id() { echo 18; }; '
                        + 'export SYSTEMROOT=' + shlex.quote(tmp) + '; '
                        + 'stat() { cat ' + shlex.quote(str(state)) + '; }; '
                        + 'cygpath() { printf "%s" "$2"; }; '
                        + 'chown() { echo "chown:$*"; '
                        + (f'echo 18 > {shlex.quote(str(state))}; ' if chown_rc == 0 else '')
                        + f'return {chown_rc}; }};\n'
                        + function + '\nopenssh_chown_service_file /test-key')
                result = bash(code)
                self.assertEqual(result.returncode, expected_rc, result.stderr)
                self.assertEqual('chown:' in result.stdout, owner != '18')
                if owner != '18':
                    self.assertIn('SYSTEM.544 /test-key', result.stdout)
                fallback = owner != '18' and chown_rc != 0
                self.assertEqual('icacls:' in result.stdout, fallback)
                if fallback:
                    self.assertIn('/test-key /setowner *S-1-5-18', result.stdout)

    def test_owner_fallback_refuses_other_service_identities(self):
        code = ('run_service_as=other; id() { echo 1000; }; stat() { echo 2000; }; '
                'chown() { return 1; }; cygpath() { echo unexpected >&2; return 9; };\n'
                + self.function('openssh_chown_service_file')
                + '\nopenssh_chown_service_file /test-key')
        result = bash(code)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('unexpected', result.stderr)


if __name__ == '__main__':
    unittest.main()
