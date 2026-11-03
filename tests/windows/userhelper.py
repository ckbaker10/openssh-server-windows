from acceptance import *
pub=(ROOT/'key.pub').read_text().strip()
config('config-helper',BASE+'AllowUsers MACHINE+Administrator\nAllowUsers DOMAIN_TEST_USER\n')
native('helper-provision',r"""
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
New-LocalUser -Name sshlocaltest -Password (ConvertTo-SecureString ([guid]::NewGuid().ToString()+'aA1!') -AsPlainText -Force) | Out-Null
[IO.File]::WriteAllText('C:\Windows\Temp\ssh-test.pub','PUB')
& .\install-user.cmd sshlocaltest C:\Windows\Temp\ssh-test.pub -ServiceName openssh-cygwin-test -Start
if($LASTEXITCODE -ne 0) { throw 'Helper failed' }
""".replace('PUB',pub))
bash('helper-record',"getent passwd sshlocaltest; id sshlocaltest; grep '^AllowUsers' /etc/sshd_config; stat -c '%u %a %n' /home/sshlocaltest /home/sshlocaltest/.ssh /home/sshlocaltest/.ssh/authorized_keys")
ssh('helper-short-login','sshlocaltest')
ssh('helper-qualified-login','MACHINE+sshlocaltest')
