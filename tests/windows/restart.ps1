$ErrorActionPreference = 'Stop'
& "$env:SystemRoot\System32\shutdown.exe" /r /t 10 /d p:4:1 /c 'Disposable SSH acceptance guest restart'
if ($LASTEXITCODE -ne 0) { throw 'Could not schedule guest restart' }
