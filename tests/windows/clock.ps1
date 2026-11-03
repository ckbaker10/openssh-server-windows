$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:COMPUTERNAME -notin @('MACHINE', 'DOMAIN-DC') -or -not (Test-Path C:\openssh-checks\lab-owned.txt)) {
    throw 'Clock synchronization is restricted to owned lab guests.'
}
$inputData = [Console]::In.ReadToEnd() | ConvertFrom-Json
$target = [DateTimeOffset]::ParseExact($inputData.utc, 'o', [Globalization.CultureInfo]::InvariantCulture)

$before = [DateTime]::UtcNow
# QEMU's RTC is UTC. Windows must interpret it consistently after a cold start.
Set-TimeZone -Id 'UTC'
Set-Date -Date $target.UtcDateTime | Out-Null
[pscustomobject]@{
    BeforeUtc = $before.ToString('o'); AfterUtc = [DateTime]::UtcNow.ToString('o'); TimeZone = (Get-TimeZone).Id
} | ConvertTo-Json
