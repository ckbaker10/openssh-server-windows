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

    def test_shell_replaces_inherited_home_from_account_lookup(self):
        # Isolate shell logic; actual Cygwin/Windows NSS needs native acceptance.
        code = ('getent() { printf "tester:x:1000:1000:Test:/tmp:/bin/bash\\n"; }; '
                'export -f getent; export HOME=/wrong-inherited-home; bash '
                + shlex.quote(str(ROOT / 'packaging/open-shell.sh'))
                + ' -c \'test "$HOME" = /tmp && test "$PWD" = /tmp\'')
        result = bash(code)
        self.assertEqual(result.returncode, 0, result.stderr)


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


if __name__ == '__main__':
    unittest.main()
