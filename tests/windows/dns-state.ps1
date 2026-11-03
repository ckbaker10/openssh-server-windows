$ErrorActionPreference='Continue'
Resolve-DnsName DOMAIN-DC.DOMAIN_DNS -Type A -DnsOnly |
    Select-Object Name,IPAddress | ConvertTo-Json -Compress
nltest.exe /dsgetdc:DOMAIN_DNS /force
