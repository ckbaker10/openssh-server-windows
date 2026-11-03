#!/usr/bin/env python3
"""Record reproducible command evidence in an ignored work directory."""
import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input', type=Path, action='append', default=[])
    parser.add_argument('--tool-version', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not argv:
        parser.error('Provide a command after --')
    dest = args.output.resolve()
    root = Path(__file__).resolve().parents[1]
    if not dest.is_relative_to(root / 'work'):
        parser.error('Output must be beneath this project\'s work/ directory')
    if (root / '.git').exists() and subprocess.run(
            ['git', '-C', str(root), 'check-ignore', '-q', str(dest)]).returncode:
        parser.error('Output must be ignored by the owning Git repository')
    inputs = []
    for p in args.input:
        with p.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        inputs.append({'path': str(p.resolve()), 'sha256': digest})
    dest.mkdir(parents=True, exist_ok=False)
    metadata = {'argv': argv, 'command': shlex.join(argv), 'cwd': str(Path.cwd()),
                'tool_version': args.tool_version, 'inputs': inputs,
                'started_epoch': int(subprocess.check_output(['date', '+%s'])), 'exit_code': None}
    metadata_path = dest / 'metadata.json'
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
    try:
        with (dest/'stdout.log').open('wb') as out, (dest/'stderr.log').open('wb') as err:
            result = subprocess.run(argv, stdout=out, stderr=err)
        metadata['exit_code'] = result.returncode
    finally:
        metadata['finished_epoch'] = int(subprocess.check_output(['date', '+%s']))
        metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
    print(metadata_path)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
