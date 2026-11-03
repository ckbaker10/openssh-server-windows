$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if (-not (Test-Path C:\openssh-checks\lab-owned.txt)) { throw 'Expected disposable lab marker' }
$certificate=New-SelfSignedCertificate -Subject 'CN=localhost' -CertStoreLocation Cert:\LocalMachine\My `
    -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 -NotAfter (Get-Date).AddDays(30) `
    -TextExtension @('2.5.29.17={text}DNS=localhost&IPAddress=127.0.0.1','2.5.29.37={text}1.3.6.1.5.5.7.3.1')
New-Item WSMan:\localhost\Listener -Transport HTTPS -Address '*' -CertificateThumbprint $certificate.Thumbprint -Force | Out-Null
netsh.exe advfirewall firewall add rule name=OpenSSH-Test-WinRM-HTTPS dir=in action=allow protocol=TCP localport=5986 remoteip=SOURCE_ADDRESS | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'HTTPS management firewall rule failed' }
[pscustomobject]@{Certificate=[Convert]::ToBase64String($certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))} | ConvertTo-Json -Compress
