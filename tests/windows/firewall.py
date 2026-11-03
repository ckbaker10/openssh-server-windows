from acceptance import *
config('config-firewall',BASE+'AllowUsers MACHINE+Administrator\n')
native('firewall-inventory',r"""
Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction | ConvertTo-Json -Compress
Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound -Action Allow | ForEach-Object {
 $rule=$_; $port=$rule | Get-NetFirewallPortFilter
 if($port.Protocol -in 'TCP','Any') {
 [pscustomobject]@{Name=$rule.Name;Port=$port.LocalPort;Program=($rule|Get-NetFirewallApplicationFilter).Program;Remote=($rule|Get-NetFirewallAddressFilter).RemoteAddress}
 }
} | ConvertTo-Json -Compress
""")
native('firewall-address-denied',"Get-NetFirewallRule -Name OpenSSH-Cygwin-Test | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress DENIED_SOURCE")
r=ssh('firewall-source-denied',expect=False,network_rejection=True)
assert b'Permission denied' not in r.stderr
native('firewall-address-list',"Get-NetFirewallRule -Name OpenSSH-Cygwin-Test | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress DENIED_SOURCE,SOURCE_CIDR")
ssh('firewall-source-list-allowed')
native('firewall-wrong-program',r"""
Disable-NetFirewallRule -Name OpenSSH-Cygwin-Test
New-NetFirewallRule -Name OpenSSH-Cygwin-TestProgram -DisplayName OpenSSH-Cygwin-TestProgram -Direction Inbound -Protocol TCP -LocalPort 2222 -RemoteAddress SOURCE_ADDRESS -Program "$env:SystemRoot\System32\OpenSSH\sshd.exe" -Action Allow | Out-Null
""")
ssh('firewall-wrong-program-denied',expect=False,network_rejection=True)
native('firewall-correct-program',"Get-NetFirewallRule -Name OpenSSH-Cygwin-TestProgram | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program 'C:\\Program Files\\OpenSSH-Cygwin\\usr\\sbin\\sshd.exe'")
ssh('firewall-correct-program-allowed')
native('firewall-restore',"Remove-NetFirewallRule -Name OpenSSH-Cygwin-TestProgram; Enable-NetFirewallRule -Name OpenSSH-Cygwin-Test")
ssh('firewall-port-allowed')
