$ErrorActionPreference = 'Stop'
$dir='C:\openssh-checks'
New-Item -ItemType Directory $dir -Force | Out-Null
icacls.exe $dir /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not protect lab directory' }
Set-Content (Join-Path $dir 'lab-owned.txt') 'Disposable OpenSSH acceptance guest'
