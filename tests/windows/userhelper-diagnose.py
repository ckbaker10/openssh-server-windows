"""Inspect the failed helper's local account without repeating provisioning."""
from acceptance import *

native('helper-local-account',r"""
$account=Get-LocalUser -Name sshlocaltest
$admins=@(Get-LocalGroupMember -SID S-1-5-32-544)
[pscustomobject]@{Enabled=$account.Enabled;SID=$account.SID.Value;Administrator=(@($admins | Where-Object {$_.SID.Value -eq $account.SID.Value}).Count -gt 0);HomeExists=(Test-Path 'C:\Program Files\OpenSSH-Cygwin\home\sshlocaltest')} | ConvertTo-Json -Compress
""")
bash('helper-name-lookup',"set +e; getent passwd sshlocaltest; echo short_getent_exit=$?; id sshlocaltest; echo short_id_exit=$?; getent passwd 'MACHINE+sshlocaltest'; echo qualified_getent_exit=$?; id 'MACHINE+sshlocaltest'; echo qualified_id_exit=$?; exit 0",system=False)
bash('helper-preserved-policy',"grep '^AllowUsers' /etc/sshd_config")
