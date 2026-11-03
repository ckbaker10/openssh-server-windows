"""Check a qualified local non-admin identity using manual key/list preparation."""
from acceptance import *

pub=(ROOT/'key.pub').read_text().strip()
script="""getent passwd 'MACHINE+sshlocaltest'
id 'MACHINE+sshlocaltest'
if id -G 'MACHINE+sshlocaltest' | tr ' ' '\\n' | grep -qx 544; then exit 2; fi
test ! -e /home/sshlocaltest
mkdir -p /home/sshlocaltest/.ssh
cat > /home/sshlocaltest/.ssh/authorized_keys <<'KEY'
PUBLIC_KEY
KEY
chown -R "$(id -u 'MACHINE+sshlocaltest')" /home/sshlocaltest
chmod 700 /home/sshlocaltest /home/sshlocaltest/.ssh
chmod 600 /home/sshlocaltest/.ssh/authorized_keys
stat -c '%u %a %n' /home/sshlocaltest /home/sshlocaltest/.ssh /home/sshlocaltest/.ssh/authorized_keys
""".replace('PUBLIC_KEY',pub)
bash('manual-nonadmin-key',script)
config('manual-nonadmin-allow',BASE+'AllowUsers MACHINE+Administrator\nAllowUsers MACHINE+sshlocaltest\nAllowUsers DOMAIN_TEST_USER\n')
groups=ssh('manual-nonadmin-login','MACHINE+sshlocaltest',command='id -G').stdout.split()
assert groups and b'544' not in groups, 'An administrator token was not excluded'
ssh('manual-short-name-denied','sshlocaltest',expect=False)
fixture=Path(__file__).with_name('fixture.txt').resolve()
dest=render('MACHINE+sshlocaltest')+'@'+CONFIG['ssh_host']
options=['-F','/dev/null','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(ROOT/'known_hosts'),
         '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=60','-i',str(KEY),'-P',str(CONFIG['ssh_port'])]
result=run_client('manual-nonadmin-scp',['scp',*options,str(fixture),dest+':manual-upload.txt'])
assert result.returncode==0, 'Non-admin SCP failed'
download=ROOT/'manual-nonadmin-download.txt'
batch=('put "'+str(fixture)+'" manual-upload.txt\nget manual-upload.txt "'+str(download)+'"\n').encode()
result=run_client('manual-nonadmin-sftp',['sftp',*options,'-b','-',dest],batch)
assert result.returncode==0 and download.read_bytes()==fixture.read_bytes(), 'Non-admin SFTP roundtrip failed'
