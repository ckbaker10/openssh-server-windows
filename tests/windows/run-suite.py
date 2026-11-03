"""Run acceptance phases in one controller process with a retained WinRM hive."""
import argparse
from pathlib import Path
import runpy
import sys
import time
import json
from lab import ROOT, ps, close_shells, _sessions

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--phases',default='auth,allow,transfers,source,firewall,userhelper')
args=parser.parse_args()
records=[]
output=ROOT/'suite-results'/str(time.time_ns())
output.mkdir(parents=True,mode=0o700)
for attempt in range(3):
    try:
        ready=ps('client',"[pscustomobject]@{DomainMember=(Get-CimInstance Win32_ComputerSystem).PartOfDomain;SecureChannel=(Test-ComputerSecureChannel)}|ConvertTo-Json -Compress")
        (output/('ready-'+str(attempt)+'.stdout')).write_bytes(ready.std_out)
        (output/('ready-'+str(attempt)+'.stderr')).write_bytes(ready.std_err)
        state=json.loads(ready.std_out.decode('utf-8-sig')) if ready.status_code==0 else {}
        if state.get('DomainMember') and state.get('SecureChannel'):
            print('Domain member and secure channel ready',flush=True)
            break
    except Exception as error:
        print('Readiness: '+type(error).__name__,flush=True)
        close_shells()
        _sessions.clear()
    if attempt==2:
        sys.exit('Domain member readiness was not established')
    time.sleep(10)
for phase in args.phases.split(','):
    start=time.time()
    old_argv=sys.argv
    try:
        if phase in ('auth','allow','source','status','setup'):
            path=Path(__file__).with_name('acceptance.py')
            sys.argv=[str(path),phase]
        elif phase in ('transfers','firewall','userhelper','local-admin-recipe','standalone','source-extra','userhelper-diagnose','manual-user'):
            path=Path(__file__).with_name(phase+'.py')
            sys.argv=[str(path)]
        else:
            raise ValueError('Unknown phase')
        runpy.run_path(str(path),run_name='__main__')
        status='passed'
    except Exception as error:
        status='failed'
        print(phase+': '+type(error).__name__,file=sys.stderr,flush=True)
    finally:
        sys.argv=old_argv
    records.append({'phase':phase,'status':status,'started_host_epoch':start,'finished_host_epoch':time.time()})
    (output/'summary.json').write_text(json.dumps(records,indent=2))
    if status=='failed':
        close_shells()
        sys.exit(1)
close_shells()
print('Suite results: '+str(output/'summary.json'))
