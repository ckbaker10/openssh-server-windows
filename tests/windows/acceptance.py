import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from lab import ROOT, ps, CONFIG, render

OUT = ROOT/'results'/str(time.time_ns())
OUT.mkdir(parents=True, mode=0o700)
records=[]

def native(label, code, machine='client', system=False):
    code = render(code)
    if system:
        raw=base64.b64encode(("$ErrorActionPreference='Stop'; try {\n"+code+"\n} catch { Write-Output $_; exit 1 }").encode()).decode()
        code = r"""
$ErrorActionPreference='Stop'
$dir='C:\openssh-checks'
New-Item -ItemType Directory $dir -Force | Out-Null
icacls.exe $dir /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Protection failed' }
$script=Join-Path $dir 'LABEL.ps1'
[IO.File]::WriteAllBytes($script,[Convert]::FromBase64String('RAW'))
$action=New-ScheduledTaskAction -Execute powershell.exe -Argument ('-NoProfile -ExecutionPolicy Bypass -Command "& ''{0}'' *> ''{1}\LABEL.log''; exit $LASTEXITCODE"' -f $script,$dir)
Register-ScheduledTask -TaskName OpenSSHTest-LABEL -Action $action -User SYSTEM -RunLevel Highest -Force | Out-Null
Start-ScheduledTask OpenSSHTest-LABEL
Start-Sleep 1
for($i=0;$i -lt 90;$i++) {
  $state=(Get-ScheduledTask OpenSSHTest-LABEL).State
  $info=Get-ScheduledTaskInfo OpenSSHTest-LABEL
  if($state -ne 'Running' -and $info.LastRunTime.Year -ge 2026) { break }
  Start-Sleep 1
}
Get-Content (Join-Path $dir 'LABEL.log')
if($state -eq 'Running') { Stop-ScheduledTask OpenSSHTest-LABEL; throw 'Task timed out; stopped the owned test task' }
Unregister-ScheduledTask OpenSSHTest-LABEL -Confirm:$false
if($info.LastTaskResult -ne 0) { throw ('Task failed '+$info.LastTaskResult) }
""".replace('LABEL',label).replace('RAW',raw)
    start=int(subprocess.check_output(['date','+%s']))
    result=ps(machine,code)
    (OUT/(label+'.ps1')).write_text(code)
    (OUT/(label+'.stdout')).write_bytes(result.std_out)
    (OUT/(label+'.stderr')).write_bytes(result.std_err)
    rec={'label':label,'exit':result.status_code,'start':start,'end':int(subprocess.check_output(['date','+%s'])),
         'script_sha256':hashlib.sha256(code.encode()).hexdigest()}
    records.append(rec); (OUT/'runs.json').write_text(json.dumps(records,indent=2))
    print(label+': '+str(result.status_code),flush=True)
    if result.status_code: raise RuntimeError('Native phase failed: '+label)
    return result.std_out.decode('utf-8-sig',errors='replace')

def bash(label,code,system=True):
    code=render(code)
    data=base64.b64encode(('set -e\nexport PATH=/usr/bin:/bin:/usr/sbin:$PATH\n'+code+'\n').encode()).decode()
    return native(label,"Set-Location 'C:\\Program Files\\OpenSSH-Cygwin'\n[IO.File]::WriteAllBytes('C:\\openssh-checks\\"+label+".sh',[Convert]::FromBase64String('"+data+"'))\n$ErrorActionPreference='Continue'\n& .\\bin\\bash.exe --noprofile --norc /cygdrive/c/openssh-checks/"+label+".sh\nif($LASTEXITCODE -ne 0) { throw 'Bash failed' }",system=system)

def config(label,body):
    body=render(body)
    raw=base64.b64encode(body.encode()).decode()
    return native(label,r"""
Stop-Service openssh-cygwin-test -ErrorAction SilentlyContinue
$root='C:\Program Files\OpenSSH-Cygwin'
$scratch='C:\openssh-checks\config'
New-Item -ItemType Directory $scratch -Force | Out-Null
[IO.File]::WriteAllBytes((Join-Path $scratch 'sshd_config'),[Convert]::FromBase64String('RAW'))
robocopy $scratch "$root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0 | Out-Null
if($LASTEXITCODE -ge 8) { throw 'Copy failed' }
& "$root\bin\bash.exe" --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if($LASTEXITCODE -ne 0) { throw 'Syntax failed' }
Start-Service openssh-cygwin-test
""".replace('RAW',raw),system=True)

KEY=ROOT/'key'
def run_client(label,cmd,data=None,retry_banner=True):
    for attempt in range(2):
        start=int(subprocess.check_output(['date','+%s']))
        try:
            r=subprocess.run(cmd,input=data,capture_output=True,timeout=120)
        except subprocess.TimeoutExpired as error:
            r=subprocess.CompletedProcess(cmd,124,error.stdout or b'',(error.stderr or b'')+b'\nHost command deadline exceeded\n')
        prefix=label+'.attempt-'+str(attempt+1)
        (OUT/(prefix+'.stdout')).write_bytes(r.stdout)
        (OUT/(prefix+'.stderr')).write_bytes(r.stderr)
        records.append({'label':label,'attempt':attempt+1,'argv':cmd,'exit':r.returncode,
                        'start':start,'end':int(subprocess.check_output(['date','+%s']))})
        (OUT/'runs.json').write_text(json.dumps(records,indent=2))
        print(prefix+': '+str(r.returncode),flush=True)
        # No authentication, command or transfer has started at this point.
        # Never repeat an interrupted command or an authentication rejection.
        if retry_banner and attempt==0 and b'timed out during banner exchange' in r.stderr:
            time.sleep(3)
            continue
        break
    (OUT/(label+'.stdout')).write_bytes(r.stdout)
    (OUT/(label+'.stderr')).write_bytes(r.stderr)
    return r


def ssh(label,user='MACHINE+Administrator',expect=True,command='id',network_rejection=False):
    user = render(user)
    cmd=['ssh','-F','/dev/null','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(ROOT/'known_hosts'),
         '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout='+('8' if network_rejection else '60'),'-i',str(KEY),'-p',str(CONFIG['ssh_port']),'-l',user,CONFIG['ssh_host'],command]
    r=run_client(label,cmd,retry_banner=not network_rejection)
    if (r.returncode==0)!=expect: raise RuntimeError('SSH unexpected result: '+label)
    if not expect and not network_rejection and b'Permission denied (publickey)' not in r.stderr:
        raise RuntimeError('Authentication rejection was not established: '+label)
    if network_rejection and not any(text in r.stderr.lower() for text in (b'timed out',b'connection refused',b'no route')):
        raise RuntimeError('Network rejection was not established: '+label)
    return r

BASE='''Port 2222
HostKey /etc/ssh_host_ed25519_key
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
StrictModes yes
UseDNS no
LogLevel VERBOSE
Subsystem sftp internal-sftp
'''

if __name__=='__main__':
    if not KEY.exists():
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(KEY)],check=True)
    action=sys.argv[1]
    if action in ('auth','allow','source'):
        native('domain-preflight',"if (-not (Get-CimInstance Win32_ComputerSystem).PartOfDomain -or -not (Test-ComputerSecureChannel)) { throw 'A healthy disposable domain member is required' }")
    if action=='status':
        for name in ('server','client'): native('status-'+name,Path(__file__).with_name('status.ps1').read_text(),machine=name)
    elif action=='setup':
        native('setup',Path(__file__).with_name('setup.ps1').read_text().replace('ARCHIVE_URL',CONFIG['archive_url']))
    elif action=='auth':
        pub=(ROOT/'key.pub').read_text().strip()
        bash('local-key',"getent passwd Administrator; getent passwd 'MACHINE+Administrator'; id 'MACHINE+Administrator'; mkdir -p /home/Administrator/.ssh; printf '%s\\n' "+shlex.quote(pub)+" > /home/Administrator/.ssh/authorized_keys; chown -R \"$(id -u 'MACHINE+Administrator')\" /home/Administrator; chmod 700 /home/Administrator /home/Administrator/.ssh; chmod 600 /home/Administrator/.ssh/authorized_keys; stat -c '%u %a %n' /home/Administrator /home/Administrator/.ssh /home/Administrator/.ssh/authorized_keys")
        config('config-open',BASE)
        ssh('local-login')
        ssh('unqualified-login','Administrator',False)
        ssh('nonexistent-login','MissingTestAccount',False)
        native('auth-log',"Get-Content 'C:\\Program Files\\OpenSSH-Cygwin\\var\\log\\sshd.log' -Tail 100",system=True)
    elif action=='allow':
        if CONFIG.get('create_domain_test_user', False):
            native('create-domain-user',"Import-Module ActiveDirectory; if (-not (Get-ADUser -Server localhost -Filter 'SamAccountName -eq \"DOMAIN_TEST_USER\"')) { New-ADUser -Server localhost -Name DOMAIN_TEST_USER -SamAccountName DOMAIN_TEST_USER -Enabled $true -AccountPassword (ConvertTo-SecureString ([guid]::NewGuid().ToString()+'aA1!') -AsPlainText -Force) }",machine='server',system=True)
        pub=(ROOT/'key.pub').read_text().strip()
        bash('domain-key',"getent passwd DOMAIN_TEST_USER; id DOMAIN_TEST_USER; mkdir -p /home/DOMAIN_TEST_USER/.ssh; printf '%s\\n' "+shlex.quote(pub)+" > /home/DOMAIN_TEST_USER/.ssh/authorized_keys; chown -R \"$(id -u DOMAIN_TEST_USER)\" /home/DOMAIN_TEST_USER; chmod 700 /home/DOMAIN_TEST_USER /home/DOMAIN_TEST_USER/.ssh; chmod 600 /home/DOMAIN_TEST_USER/.ssh/authorized_keys")
        config('config-domain-baseline',BASE)
        ssh('domain-valid-key','DOMAIN_TEST_USER')
        config('config-local-only',BASE+'AllowUsers MACHINE+Administrator\n')
        ssh('allow-local')
        ssh('deny-domain','DOMAIN_TEST_USER',False)
        config('config-multiple',BASE+'AllowUsers MACHINE+Administrator\nAllowUsers DOMAIN_TEST_USER\n')
        ssh('multiple-local')
        ssh('multiple-domain','DOMAIN_TEST_USER')
    elif action=='source':
        config('config-user-address',BASE+'AllowUsers MACHINE+Administrator@SOURCE_ADDRESS\n')
        ssh('source-address-allowed')
        config('config-user-cidr',BASE+'AllowUsers MACHINE+Administrator@SOURCE_CIDR\n')
        ssh('source-cidr-allowed')
        config('config-user-list',BASE+'AllowUsers MACHINE+Administrator@DENIED_SOURCE MACHINE+Administrator@SOURCE_CIDR\n')
        ssh('source-list-allowed')
        config('config-user-usedns',BASE.replace('UseDNS no','UseDNS yes')+'AllowUsers MACHINE+Administrator@SOURCE_ADDRESS\n')
        ssh('source-usedns-allowed')
        config('config-user-denied',BASE+'AllowUsers MACHINE+Administrator@DENIED_SOURCE\n')
        ssh('source-address-denied',expect=False)
        config('config-unrestricted-union',BASE+'AllowUsers MACHINE+Administrator@DENIED_SOURCE\nAllowUsers MACHINE+Administrator\n')
        ssh('source-unrestricted-union')
        config('config-match-allowed',BASE+'AllowUsers MACHINE+Administrator\nMatch Address *,!SOURCE_ADDRESS,!198.51.100.0/24\n    DenyUsers *\n')
        ssh('match-source-allowed')
        config('config-match-denied',BASE+'AllowUsers MACHINE+Administrator\nMatch Address *,!DENIED_SOURCE,!198.51.100.0/24\n    DenyUsers *\n')
        ssh('match-source-denied',expect=False)
        native('source-log',"Get-Content 'C:\\Program Files\\OpenSSH-Cygwin\\var\\log\\sshd.log' -Tail 100",system=True)
        config('config-final',BASE+'AllowUsers MACHINE+Administrator\n')
