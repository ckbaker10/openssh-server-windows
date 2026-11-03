"""Prove a documentation repack retained every non-documentation payload byte."""
from pathlib import PurePosixPath
import sys
import zipfile

EXCLUDED = {'INSTALLATION.md', 'NONADMIN-USERS.md', 'TROUBLESHOOTING.md',
            'COMPILE.md', 'SHA256SUMS', 'build-manifest.json'}


def payload(filename):
    with zipfile.ZipFile(filename) as archive:
        assert archive.testzip() is None
        files = [name for name in archive.namelist() if not name.endswith('/')]
        roots = {PurePosixPath(name).parts[0] for name in files}
        assert len(roots) == 1, 'Expected one installation directory'
        return {'/'.join(PurePosixPath(name).parts[1:]): archive.read(name)
                for name in files}


before, after = (payload(name) for name in sys.argv[1:])
assert before.keys() == after.keys(), 'Runtime file list changed'
checked = 0
for name in before:
    if name not in EXCLUDED:
        assert before[name] == after[name], 'Runtime bytes changed: ' + name
        checked += 1
print(str(checked) + ' runtime files are byte-identical; only guides and their manifests may differ')
