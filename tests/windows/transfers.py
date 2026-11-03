from acceptance import *

def transfer(label,kind,user,expect):
    fixture=Path(__file__).with_name('fixture.txt').resolve()
    dest=render(user)+'@'+CONFIG['ssh_host']
    options=['-F','/dev/null','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(ROOT/'known_hosts'),
             '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=60','-i',str(KEY)]
    if kind=='scp':
        cmd=['scp',*options,'-P',str(CONFIG['ssh_port']),str(fixture),dest+':upload.txt']; data=None
    else:
        cmd=['sftp',*options,'-P',str(CONFIG['ssh_port']),'-b','-',dest]
        data=('put "'+str(fixture)+'" upload.txt\nget upload.txt "'+str(ROOT/(label+'-download.txt'))+'"\n').encode()
    r=run_client(label,cmd,data)
    if (r.returncode==0)!=expect: raise RuntimeError('Unexpected transfer result')
    if not expect and b'Permission denied (publickey)' not in r.stderr:
        raise RuntimeError('Transfer authentication rejection was not established')
    if kind=='sftp' and expect:
        assert (ROOT/(label+'-download.txt')).read_bytes()==fixture.read_bytes()
    records.append({'label':label,'argv':cmd,'exit':r.returncode,'expected_success':expect})
    (OUT/'transfers.json').write_text(json.dumps(records,indent=2))

config('config-transfer',BASE+'AllowUsers MACHINE+Administrator\n')
for kind in ('scp','sftp'):
    transfer('allowed-'+kind,kind,'MACHINE+Administrator',True)
    transfer('denied-'+kind,kind,'DOMAIN_TEST_USER',False)
native('transfer-log',"Get-Content 'C:\\Program Files\\OpenSSH-Cygwin\\var\\log\\sshd.log' -Tail 100",system=True)
