"""Bounded read-only WinRM readiness check following a lab guest restart."""
import json
import sys
import time
from lab import ROOT, ps, _sessions, close_shells

machine = sys.argv[1]
output = ROOT/'readiness'/str(time.time_ns())
output.mkdir(parents=True,mode=0o700)
for attempt in range(3):
    try:
        result = ps(machine, "[pscustomobject]@{PartOfDomain=(Get-CimInstance Win32_ComputerSystem).PartOfDomain;SecureChannel=(Test-ComputerSecureChannel)} | ConvertTo-Json -Compress")
        (output/(str(attempt)+'.stdout')).write_bytes(result.std_out)
        (output/(str(attempt)+'.stderr')).write_bytes(result.std_err)
        if result.status_code == 0:
            record = json.loads(result.std_out.decode('utf-8-sig'))
            print('Readiness: '+json.dumps(record),flush=True)
            if record['PartOfDomain'] and record['SecureChannel']:
                print('Domain member WinRM ready: '+machine)
                sys.exit(0)
    except Exception as error:
        print('Readiness attempt '+str(attempt+1)+': '+type(error).__name__,flush=True)
        close_shells()
        _sessions.pop(machine, None)
    if attempt < 2:
        time.sleep(10)
sys.exit('Guest readiness was not established')
