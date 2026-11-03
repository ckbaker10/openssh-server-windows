$ErrorActionPreference = 'Stop'
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{OS=$os.Caption;Version=$os.Version;Build=$os.BuildNumber;DomainMember=$cs.PartOfDomain;Name=$cs.Name} | ConvertTo-Json -Compress
