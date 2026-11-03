$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$scratch=Join-Path $env:TEMP ('openssh-candidate-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
$zip=Join-Path $scratch 'candidate.zip'
Invoke-WebRequest -UseBasicParsing 'ARCHIVE_URL' -OutFile $zip
$hash=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
if($hash -ne 'CANDIDATE_SHA256') { throw 'Downloaded candidate ZIP hash differs' }
Expand-Archive -LiteralPath $zip -DestinationPath $scratch
$root=Join-Path $scratch 'OpenSSH-Cygwin'
if(-not(Test-Path (Join-Path $root 'install-server.cmd'))) { throw 'Unexpected archive directory layout' }
if(Test-Path (Join-Path $root 'tests')) { throw 'Test suite found in runtime ZIP' }
if(Test-Path (Join-Path $root 'TESTING.md')) { throw 'Testing guide found in runtime ZIP' }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'verify-package.ps1')
if($LASTEXITCODE -ne 0) { throw 'Native candidate payload verification failed' }
[pscustomobject]@{ZIP_SHA256=$hash;Layout='OpenSSH-Cygwin';Verifier='PASS';PowerShell=$PSVersionTable.PSVersion.ToString()}|ConvertTo-Json -Compress
