"""Regression cases for names ordinary Windows ZIP extractors cannot create."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'package', Path(__file__).resolve().parents[1] / 'scripts' / 'package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class WindowsArchivePaths(unittest.TestCase):
    def test_runtime_and_license_paths(self):
        package.validate_windows_paths([
            'bin/[.exe', 'usr/sbin/sshd.exe', 'usr/share/doc/openssh/LICENCE'])

    def test_rejects_manuals_and_unextractable_names(self):
        for name in [
            'usr/share/man/man1/:.1.gz', 'usr/share/man/man1/ssh.1',
            'usr/share/info/bash.info.gz', 'bin/NUL.txt', 'bin/COM1.exe',
            'bin/aux.txt', 'bin/invalid:name', 'bin/trailing.', 'bin/trailing ',
            'bin/../sshd.exe', '/bin/sshd.exe', 'bin/bad\x00name',
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                package.validate_windows_paths([name])

    def test_rejects_windows_case_collisions(self):
        with self.assertRaises(ValueError):
            package.validate_windows_paths(['bin/SSH.EXE', 'bin/ssh.exe'])

    def test_identical_readme_alias_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README').write_bytes(b'license and documentation')
            (root / 'readme').write_bytes(b'license and documentation')
            self.assertEqual(package.deduplicate_windows_files(root), ['readme'])
            self.assertEqual((root / 'README').read_bytes(), b'license and documentation')

    def test_different_case_colliding_files_are_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README').write_bytes(b'first')
            (root / 'readme').write_bytes(b'second')
            with self.assertRaises(ValueError):
                package.deduplicate_windows_files(root)
            self.assertEqual((root / 'readme').read_bytes(), b'second')


if __name__ == '__main__':
    unittest.main()
