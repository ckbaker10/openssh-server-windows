$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:COMPUTERNAME -ne 'MACHINE' -or -not (Test-Path C:\openssh-checks\lab-owned.txt)) {
    throw 'This network configuration belongs to the owned lab client.'
}
$private = @(Get-NetAdapter | Where-Object MacAddress -eq '52-54-00-AA-20-02')
$management = @(Get-NetAdapter | Where-Object MacAddress -eq '52-54-00-AA-20-01')
if ($private.Count -ne 1 -or $management.Count -ne 1) { throw 'Unexpected lab NIC identity.' }
$existing = @(Get-NetIPAddress -InterfaceIndex $private.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '169.254.*' })
if (@($existing | Where-Object IPAddress -ne 'CLIENT_PRIVATE_ADDRESS').Count) { throw 'Private NIC already has another static address.' }
if (-not $existing.Count) {
    New-NetIPAddress -InterfaceIndex $private.ifIndex -IPAddress CLIENT_PRIVATE_ADDRESS -PrefixLength 24 | Out-Null
}
Set-DnsClient -InterfaceIndex $management.ifIndex -RegisterThisConnectionsAddress $false
Set-DnsClient -InterfaceIndex $private.ifIndex -RegisterThisConnectionsAddress $true
$deadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    $address = Get-NetIPAddress -InterfaceIndex $private.ifIndex -AddressFamily IPv4 |
        Where-Object IPAddress -eq 'CLIENT_PRIVATE_ADDRESS'
    if ($address.AddressState -eq 'Preferred') { break }
    Start-Sleep -Seconds 1
} while ([DateTime]::UtcNow -lt $deadline)
if ($address.AddressState -ne 'Preferred') { throw 'Private client address did not become usable.' }
if (-not (Test-NetConnection SERVER_PRIVATE_ADDRESS -Port 53 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    throw 'The private domain DNS server is unreachable; check the owned QEMU socket link.'
}
Set-DnsClientServerAddress -InterfaceIndex $private.ifIndex -ServerAddresses SERVER_PRIVATE_ADDRESS
Set-DnsClientServerAddress -InterfaceIndex $management.ifIndex -ServerAddresses SERVER_PRIVATE_ADDRESS
$answer = Resolve-DnsName -Name '_ldap._tcp.dc._msdcs.DOMAIN_DNS' -Type SRV -Server SERVER_PRIVATE_ADDRESS -DnsOnly
if (-not ($answer | Where-Object NameTarget -eq 'DOMAIN-DC.DOMAIN_DNS')) { throw 'The isolated AD locator record was not resolved.' }
[pscustomobject]@{ PrivateAddress = 'CLIENT_PRIVATE_ADDRESS'; DomainDns = 'SERVER_PRIVATE_ADDRESS'; DomainLocatorVerified = $true } | ConvertTo-Json
