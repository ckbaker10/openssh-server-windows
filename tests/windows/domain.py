"""Promote/join only marked disposable guests; domain credentials use encrypted stdin."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys
from lab import ROOT, CONFIG, ps


def call(machine, filename, payload=b''):
    source=Path(__file__).with_name(filename)
    result=ps(machine,source.read_text(),payload)
    output=ROOT/'domain-results'
    output.mkdir(mode=0o700,exist_ok=True)
    (output/(filename+'-'+machine+'.stdout')).write_bytes(result.std_out)
    (output/(filename+'-'+machine+'.stderr')).write_bytes(result.std_err)
    print(filename+' '+machine+': '+str(result.status_code),flush=True)
    if result.status_code:
        raise RuntimeError('Domain setup failed; inspect private logs before retrying')


def save(path, data):
    path.write_text(json.dumps(data))
    os.chmod(path,0o600)


def main():
    action=sys.argv[1]
    if action=='mark':
        for machine in ('server','client'):
            call(machine,'mark-lab.ps1')
    elif action=='clock':
        for machine in ('server','client'):
            utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')+'0+00:00'
            call(machine,'clock.ps1',json.dumps({'utc':utc}).encode())
    elif action=='promote':
        path=ROOT/'server'/'credentials.json'
        account=json.loads(path.read_text())
        account['dsrm_password']=secrets.token_urlsafe(32)+'aA1!'
        save(path,account)
        call('server','initialize-forest.ps1',json.dumps({'dsrm_password':account['dsrm_password']}).encode())
        account['username']=CONFIG['domain_netbios']+'\\'+CONFIG.get('domain_admin_name','Administrator')
        save(path,account)
    elif action=='domain-identity':
        path=ROOT/'server'/'credentials.json'
        account=json.loads(path.read_text())
        account['username']=CONFIG['domain_netbios']+'\\'+CONFIG.get('domain_admin_name','Administrator')
        save(path,account)
    elif action=='join':
        call('client','client-network.ps1')
        account=json.loads((ROOT/'server'/'credentials.json').read_text())
        expected=CONFIG['domain_netbios']+'\\'+CONFIG.get('domain_admin_name','Administrator')
        if account['username'] != expected:
            raise ValueError('Use the test domain Administrator for joining')
        call('client','join-client.ps1',json.dumps({key:account[key] for key in ('username','password')}).encode())
    else:
        raise ValueError('Use mark, clock, promote or join')


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print('Domain setup failed: '+type(error).__name__,file=sys.stderr)
        sys.exit(1)
