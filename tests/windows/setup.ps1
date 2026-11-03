$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = 'C:\Program Files\OpenSSH-Cygwin'
if (-not (Test-Path $root)) {
Invoke-WebRequest -UseBasicParsing 'ARCHIVE_URL' -OutFile C:\Windows\Temp\openssh-test.zip
Get-FileHash C:\Windows\Temp\openssh-test.zip -Algorithm SHA256 | Select-Object Hash | ConvertTo-Json -Compress
Expand-Archive C:\Windows\Temp\openssh-test.zip -DestinationPath 'C:\Program Files'
}
Set-Location $root
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verify-package.ps1
if ($LASTEXITCODE -ne 0) { throw 'Verifier failed' }
& .\install-server.cmd --yes --name openssh-cygwin-test --port 2222
$installExit = $LASTEXITCODE
Write-Output "INSTALL_EXIT=$installExit"
Get-CimInstance Win32_Service -Filter "Name='openssh-cygwin-test'" | Select-Object Name,StartName,StartMode,State | ConvertTo-Json -Compress
Get-Item .\etc\sshd_config, .\etc\ssh_host_*_key | Get-Acl | Select-Object Owner | ConvertTo-Json -Compress
& .\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; getent passwd Administrator; getent passwd "MACHINE+Administrator"; id "MACHINE+Administrator"; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) { throw 'Lookup or syntax check failed' }
New-NetFirewallRule -Name OpenSSH-Cygwin-Test -DisplayName OpenSSH-Cygwin-Test -Direction Inbound -Protocol TCP -LocalPort 2222 -Action Allow -RemoteAddress SOURCE_ADDRESS | Out-Null
Enable-LocalUser -Name Administrator
Set-LocalUser -Name Administrator -Password (ConvertTo-SecureString ([guid]::NewGuid().ToString()+'aA1!') -AsPlainText -Force)
