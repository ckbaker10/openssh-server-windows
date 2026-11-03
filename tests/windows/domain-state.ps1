$ErrorActionPreference='Continue'
Get-Service NTDS,ADWS,DNS | Select-Object Name,Status | ConvertTo-Json -Compress
Get-ScheduledTask -TaskName OpenSSHTest-create-domain-user -ErrorAction SilentlyContinue |
    Select-Object TaskName,State | ConvertTo-Json -Compress
Get-Content C:\openssh-checks\create-domain-user.log -Tail 15 -ErrorAction SilentlyContinue
