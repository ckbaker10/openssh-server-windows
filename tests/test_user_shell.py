"""Exercise the shell boundary without touching system account files."""
from pathlib import Path
import shlex
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'packaging/install-user.sh'


class UserShell(unittest.TestCase):
    def run_shell(self, code):
        return subprocess.run(['bash', '-c', 'source ' + shlex.quote(str(SCRIPT)) + '; ' + code], text=True, capture_output=True)

    def test_administrator_is_rejected(self):
        result = self.run_shell('id() { echo "1000 544"; }; getent() { echo unexpected; }; inspect_user sshtest')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('unexpected', result.stdout)

    def test_local_account_record_is_returned(self):
        result = self.run_shell('id() { echo "1000 545"; }; getent() { echo account-record; }; inspect_user sshtest')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'account-record')

    def test_changed_home_stops_before_chmod(self):
        result = self.run_shell('inspect_user() { echo "sshtest:*:1000:545:comment:/wrong:/bin/bash"; }; chmod() { echo unexpected; }; configure_user sshtest 1000')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('unexpected', result.stdout)

    def test_modes_and_owner_checks(self):
        code = '''inspect_user() { echo 'sshtest:*:1000:545:comment:/home/sshtest:/bin/bash'; };
        stat() { if [[ $2 == %u ]]; then echo 1000; elif [[ $3 == */authorized_keys ]]; then echo 600; else echo 700; fi; };
        chmod() { echo "chmod:$*"; }; configure_user sshtest 1000'''
        result = self.run_shell(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('chmod:600 /home/sshtest/.ssh/authorized_keys', result.stdout)
        self.assertIn('chmod:700 /home/sshtest/.ssh /home/sshtest', result.stdout)


if __name__ == '__main__':
    unittest.main()
