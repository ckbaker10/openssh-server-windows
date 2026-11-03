"""Verify the exact final host ZIP through Windows PowerShell without installing it."""
import hashlib
import json
from pathlib import Path
import sys
from lab import ROOT, CONFIG, ps, session

candidate=Path(sys.argv[1])
with candidate.open('rb') as stream:
    CONFIG['candidate_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
(ROOT/'config.json').write_text(json.dumps(CONFIG,indent=2)+'\n')
# Extraction plus hashing can exceed the short control-request deadline on
# an I/O-bound guest. Keep certificate validation and the WinRM operation
# timeout unchanged, but allow this one final verification to finish.
session('client').protocol.transport.read_timeout_sec=600
result=ps('client',Path(__file__).with_suffix('.ps1').read_text())
output=ROOT/'candidate-verification'
output.mkdir(exist_ok=True,mode=0o700)
(output/'stdout.log').write_bytes(result.std_out)
(output/'stderr.log').write_bytes(result.std_err)
if result.status_code:
    sys.exit('Native candidate verification failed; inspect private logs')
print(result.std_out.decode('utf-8-sig').strip())
