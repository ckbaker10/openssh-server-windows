$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:COMPUTERNAME -ne 'MACHINE' -or -not (Test-Path C:\openssh-checks\lab-owned.txt)) {
    throw 'Domain join is restricted to the owned lab client.'
}
$system = Get-CimInstance Win32_ComputerSystem
if ($system.PartOfDomain) { throw 'Client already belongs to a domain; refusing a second join.' }
if (-not (Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq 'CLIENT_PRIVATE_ADDRESS')) {
    throw 'Configure and verify the private client network first.'
}
$inputData = [Console]::In.ReadToEnd() | ConvertFrom-Json
if ($inputData.username -ne 'DOMAIN\DOMAIN_ADMIN_NAME' -or [string]::IsNullOrWhiteSpace($inputData.password)) {
    throw 'Unexpected lab domain account.'
}
$secure = ConvertTo-SecureString $inputData.password -AsPlainText -Force
$credential = [PSCredential]::new($inputData.username, $secure)
try {
    $result = Add-Computer -DomainName 'DOMAIN_DNS' `
        -Credential $credential -PassThru -Force -ErrorAction Stop
    if (-not $result.HasSucceeded) { throw 'Domain join was not successful.' }
    [pscustomobject]@{ Joined = $true; Domain = 'DOMAIN_DNS'; RestartPending = $true } | ConvertTo-Json
    & shutdown.exe /r /t 20 /d p:2:4 /c 'Owned SSH lab domain join'
    if ($LASTEXITCODE) { throw 'Cannot schedule client restart.' }
} finally {
    $credential = $null
    $inputData = $null
    $secure.Dispose()
}
