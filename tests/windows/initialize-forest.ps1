$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:COMPUTERNAME -ne 'DOMAIN-DC' -or -not (Test-Path C:\openssh-checks\lab-owned.txt)) {
    throw 'Forest creation is restricted to the owned DOMAIN-DC guest.'
}
$computer = Get-CimInstance Win32_ComputerSystem
if ($computer.PartOfDomain) { throw 'A domain is already present; refusing a second promotion.' }
$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($payload.dsrm_password)) { throw 'A protected recovery credential is required on stdin.' }
$recovery = ConvertTo-SecureString $payload.dsrm_password -AsPlainText -Force
$payload = $null
try {
    $private = @(Get-NetAdapter | Where-Object MacAddress -EQ '52-54-00-AA-10-02')
    $management = @(Get-NetAdapter | Where-Object MacAddress -EQ '52-54-00-AA-10-01')
    if ($private.Count -ne 1 -or $management.Count -ne 1) { throw 'Expected lab network adapters are missing.' }
    $index = $private[0].ifIndex
    $existing = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '169.254.*' })
    if ($existing | Where-Object IPAddress -NE 'SERVER_PRIVATE_ADDRESS') { throw 'Unexpected private adapter configuration.' }
    if (-not ($existing | Where-Object IPAddress -EQ 'SERVER_PRIVATE_ADDRESS')) {
        New-NetIPAddress -InterfaceIndex $index -IPAddress SERVER_PRIVATE_ADDRESS -PrefixLength 24 | Out-Null
    }
    Set-DnsClient -InterfaceIndex $management[0].ifIndex -RegisterThisConnectionsAddress $false
    Set-DnsClient -InterfaceIndex $index -RegisterThisConnectionsAddress $true
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Get-NetIPAddress -InterfaceIndex $index -IPAddress SERVER_PRIVATE_ADDRESS -ErrorAction SilentlyContinue |
            Where-Object AddressState -EQ 'Preferred') { break }
        Start-Sleep -Seconds 1
    }
    if (-not (Get-NetIPAddress -InterfaceIndex $index -IPAddress SERVER_PRIVATE_ADDRESS |
        Where-Object AddressState -EQ 'Preferred')) { throw 'Private lab address did not become ready.' }
    $dns = Get-DnsServerSetting -All
    $dns.ListeningIpAddress = @('SERVER_PRIVATE_ADDRESS')
    Set-DnsServerSetting $dns
    Set-DnsServerForwarder -IPAddress 10.0.2.3
    Enable-LocalUser -Name Administrator
    Install-ADDSForest -DomainName 'DOMAIN_DNS' -DomainNetbiosName 'DOMAIN' -InstallDns `
        -CreateDnsDelegation:$false -SafeModeAdministratorPassword $recovery -NoRebootOnCompletion -Force | Out-Null
    Set-DnsClientServerAddress -InterfaceIndex $index -ServerAddresses SERVER_PRIVATE_ADDRESS
    Set-DnsClientServerAddress -InterfaceIndex $management[0].ifIndex -ServerAddresses SERVER_PRIVATE_ADDRESS
    [pscustomobject]@{ PromotionCompleted = $true; Domain = 'DOMAIN_DNS'; RebootScheduled = $true } | ConvertTo-Json -Compress
    & "$env:SystemRoot\System32\shutdown.exe" /r /t 20 /d p:4:1
    if ($LASTEXITCODE) { throw 'Promotion completed but planned restart was rejected.' }
} finally {
    $recovery.Dispose()
}
