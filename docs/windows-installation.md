# Installation and operation on Windows

Requirements: Windows x86_64, Windows PowerShell 5.1 and elevated administrator
rights for setup. The package includes Cygwin and Bash; neither the optional
Windows OpenSSH feature nor the Microsoft SDK is required. The service runs
as LocalSystem; logins use the permissions of the respective Windows account.

## Extract and verify

Download the ZIP and SHA256SUMS from the same release. Compare the hash:

```powershell
Get-FileHash .\openssh-10.6p1-cygwin-x86_64.zip -Algorithm SHA256
```

The ZIP contains a single top-level `OpenSSH-Cygwin` directory. Extract into
`C:\Program Files` to obtain `C:\Program Files\OpenSSH-Cygwin` without renaming.
`install-server.cmd` and `bin\cygwin1.dll` must be directly beneath that
directory; avoid an extra `OpenSSH-Cygwin\OpenSSH-Cygwin` level. Only
Administrators and SYSTEM should be able to modify this
installation tree. Then verify it in PowerShell:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verify-package.ps1
if ($LASTEXITCODE -ne 0) { throw 'Package verification failed' }
```

The verifier is unsigned. Without the process-specific `-ExecutionPolicy Bypass`,
PowerShell can reject it with "not digitally signed", for example when the
extracted script is marked as downloaded from the Internet. This option changes
only the verifier process's policy; it does not change the saved user or machine
policy or disable the verifier's hash checks.

An execution policy enforced by Group Policy takes precedence over this option.
If the script is still blocked, inspect `Get-ExecutionPolicy -List` and ask your
administrator for an approved execution method when `MachinePolicy` or
`UserPolicy` enforces signing. See Microsoft's
[execution-policy documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1).
Continue with setup only after verification succeeds.

Specify `-Path 'C:\Program Files\OpenSSH-Cygwin'` explicitly if needed.
The verifier reads SHA256SUMS without JSON. An empty list, missing files or
modified payload files cause failure. The payload list excludes itself and
the manifest; the manifest also covers the list. The ZIP hash covers everything.
Configuration changes during setup, so compare only unmodified packages.

## Set up the service

In elevated 64-bit PowerShell, inside the installation directory:

```powershell
.\install-server.cmd --yes --name openssh-cygwin --port 2222
```

`--user`, `--pwd` and `--privileged` are rejected. No additional service account
is created. Without `--port`, an existing port is preserved; new configurations
use 22. `--port 22` explicitly changes the port back to 22.
`--yes` preserves existing sshd_config, ssh_config and nsswitch.conf, backing
them up under `etc\backups\<UTC>-<ID>`. Missing files are copied from
`etc\defaults\etc`. An explicit port option changes the server configuration.

Stop a running service with the same name first. An existing registration keeps
its executable path and arguments; use the update procedure when moving it.

New registrations use **Automatic (Delayed Start)** and depend on TCP/IP.
The delay reduces exposure to early boot failures; it does not prove that
Windows authentication and profile services are ready. Existing registrations
keep their startup settings. To change only the startup mode of your existing
service, run `sc.exe config openssh-cygwin start= delayed-auto` and check
`$LASTEXITCODE`. Do not replace its dependency list blindly.

The installer retains ssh-host-config's error/warning count as its exit code.
An additional startup-configuration failure also returns nonzero. A service
can be registered and pass `sshd -t` while ownership repairs have failed.
Read all diagnostics and complete the checks below before starting it.

## Verify SYSTEM ownership

Check sshd_config and every private host key after setup and upgrades:

```powershell
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$Files = @((Join-Path $Root 'etc\sshd_config')) + @(
    Get-ChildItem -LiteralPath "$Root\etc" -Filter 'ssh_host_*_key' -File |
        Select-Object -ExpandProperty FullName
)
foreach ($File in $Files) {
    $Acl = Get-Acl -LiteralPath $File -ErrorAction Stop
    [pscustomobject]@{ Path = $File; Owner = $Acl.Owner }
    if ($Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne 'S-1-5-18') {
        Write-Warning "Expected SYSTEM owner: $File"
    }
}
```

The expected owner is SYSTEM (SID S-1-5-18). The installer first tries Cygwin
chown, then icacls /setowner on that exact file, and verifies the resulting UID.
It reports failures rather than treating a running service as proof of success.
If the fallback is denied, use an elevated local console; if necessary, execute
the same repair as SYSTEM through a controlled administrative task:

```powershell
icacls.exe "$Root\etc\sshd_config" /setowner '*S-1-5-18'
if ($LASTEXITCODE -ne 0) { throw 'SYSTEM owner repair failed' }
```

Repeat only for each incorrectly owned private key, then check owners and
`sshd -t` again. Do not grant broad read access or recursively change the tree.
SSH administrator sessions can have different backup/restore privileges from
a local console. Robocopy /B /COPY:DAT preserves the existing owner, including
an incorrect one; it is not an ownership repair.

## Set up an administrator's key

Open the bundled shell as the target user:

```powershell
.\open-shell.cmd
```

It sets HOME from the Cygwin account database. `etc\nsswitch.conf` specifies
`/home/%U` and Bash. Existing `/etc/passwd` entries take precedence. In Bash:

```bash
id
getent passwd "$(id -u)"
printf '%s\n' "$HOME"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME" "$HOME/.ssh"
cat >> "$HOME/.ssh/authorized_keys" <<'KEY'
ssh-ed25519 AAAA...replace_with_your_own_public_key
KEY
chmod 600 "$HOME/.ssh/authorized_keys"
exit
```

Insert a real public key, never a private key. For restricted accounts, use
the separate helper described in NONADMIN-USERS.md.

Files previously created with PowerShell may be owned by the Administrators
group, preventing Cygwin chmod. Correct ownership only on the affected user's
home directory, then set the permissions again in Bash:

```powershell
$Account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$UserHome = 'C:\Program Files\OpenSSH-Cygwin\home\Administrator'
icacls.exe $UserHome /setowner $Account /t /c
if ($LASTEXITCODE -ne 0) { throw 'Ownership change failed' }
```

This example applies to your own account; specify the target account name
when preparing another user's home. Never assign the whole installation tree
to a regular user. Keep StrictModes enabled.

## Domain members and account selection

On a domain member, an unqualified name such as Administrator can resolve to
the domain account. A local account may be named `MACHINE+Administrator` in
Cygwin. Inspect `getent passwd 'MACHINE+Administrator'` and
`id 'MACHINE+Administrator'` in the bundled shell; verify the Windows SID,
UID and home before installing a key. Use the exact Cygwin name in AllowUsers
and connect with `ssh -l 'MACHINE+Administrator' server.example`.

The compatibility default `db_home: /home/%U` uses the Windows account name.
Local and domain accounts with that name can therefore share the same home
path even though their SIDs differ. Never infer the home from the qualified
login name or put keys for different identities into a shared home.

Cygwin supports `db_home: /home/%D/%U`, where %D is the NetBIOS domain and %U
the Windows name. It separates domain and machine identities. This package
does not switch existing installations automatically: changing it redirects
homes for all database accounts and can lock users out. For a planned migration,
stop the service, back up NSS/configuration/homes with their ACLs, change NSS,
open a fresh bundled shell and inspect each account's new passwd record. Move
each account's data and keys to its resolved home with the correct owner and
700/700/600 permissions; test every intended identity before removing old data.
Explicit /etc/passwd records take precedence. Restart processes to reread NSS.

The install-user helper supports only the documented existing local-account
`/home/NAME` layout. It rejects qualified names, unexpected homes or a SID
mismatch; configure domain/qualified accounts and alternative layouts manually.
This prevents an ambiguous name from provisioning the wrong identity.
[Cygwin account and home settings](https://cygwin.com/cygwin-ug-net/ntsec.html).

### Local administrator on a domain member

If the bundled shell already runs as the intended account, resolve its numeric
UID instead of guessing a Windows or Cygwin name:

```bash
export PATH=/usr/bin:/bin:/usr/sbin:$PATH
id -un
getent passwd "$(id -u)"
```

This identifies the shell's current account, which may be a domain account.
Elevation alone does not select the local built-in administrator.

To select the **local built-in administrator** from another administrative
account, use elevated 64-bit PowerShell in the installation directory:

```powershell
$ErrorActionPreference = 'Stop'
if ((Get-CimInstance Win32_ComputerSystem).DomainRole -ge 4) {
    throw 'A domain controller has no local SAM administrator account'
}
$Local = @(Get-LocalUser | Where-Object { $_.SID.Value -match '-500$' })
if ($Local.Count -ne 1) { throw 'Expected one local built-in administrator' }
$Name = $env:COMPUTERNAME + '+' + $Local[0].Name
$Record = & .\bin\getent.exe passwd $Name
if ($LASTEXITCODE -ne 0) { throw 'Cygwin account lookup failed' }
$Fields = $Record -split ':'
if ($Fields.Count -ne 7 -or ($Fields[4] -split ',')[-1] -ne $Local[0].SID.Value) {
    throw 'Cygwin account SID does not match the selected Windows account'
}
[pscustomobject]@{
    Login = $Fields[0]; UID = $Fields[2]; Home = $Fields[5]
    SID = $Local[0].SID.Value; Enabled = $Local[0].Enabled
}
```

This discovers the computer prefix and the account's current name, including
renamed built-in administrators, and checks the complete SID rather than only
the name. It does not enable an account or change keys, homes or permissions.
Use the returned Login in AllowUsers and `ssh -l`, and review the returned Home
for collisions before installing a key. A successful lookup is not a successful
SSH login; disabled accounts remain disabled. This selection is specifically
for the built-in account, not every member of the Administrators group.

For manual comparison of the unqualified and local names:

This procedure was checked on a Windows 11 domain member with this Cygwin
build. Windows Server 2022 behavior still needs separate validation.
In an administrative bundled Bash session, inspect both identities first:

```bash
export PATH=/usr/bin:/bin:/usr/sbin:$PATH
getent passwd Administrator
getent passwd 'MACHINE+Administrator'
id 'MACHINE+Administrator'
```

Replace MACHINE with the computer name. Confirm the SID belongs to the local
computer, record the local UID, and use the home returned by getent. With the
default NSS setting, both records can show `/home/Administrator`; a directory
name does not establish which identity owns it. Stop if this home contains
another account's data. Back it up with owners and ACLs before any reassignment.
Do not recursively assign an existing shared home without reviewing its contents.

For a home deliberately assigned to the local account, install only its public
key and set ownership to the **local** UID, then permissions to 700/700/600:

```bash
mkdir -p /home/Administrator/.ssh
cat >> /home/Administrator/.ssh/authorized_keys <<'KEY'
ssh-ed25519 AAAA...replace_with_your_own_public_key
KEY
chown -R "$(id -u 'MACHINE+Administrator')" /home/Administrator
chmod 700 /home/Administrator /home/Administrator/.ssh
chmod 600 /home/Administrator/.ssh/authorized_keys
stat -c '%u %a %n' /home/Administrator /home/Administrator/.ssh /home/Administrator/.ssh/authorized_keys
```

Keep StrictModes enabled. Verify numeric ownership rather than guessing from
the displayed primary group. Test the explicit account from a second client:

```bash
ssh -p 2222 -l 'MACHINE+Administrator' server.example id
```

Use the same exact Cygwin account name in AllowUsers. An unqualified
Administrator selected the domain identity in the checked case, and could
not use the local account's key file. The server logged a bad ownership/modes
rejection. `Permission denied (publickey)` also occurred for a nonexistent
account, so it does not establish that a username exists. See
TROUBLESHOOTING.md for the reported connection-close variation and its limits.
The `/home/%D/%U` alternative above requires a planned, backed-up migration;
do not change NSS as an incidental key-installation step.

## Check, start and connect

Every Bash invocation without profiles needs the Cygwin PATH. Use single quotes
in PowerShell so that Bash expands `$PATH`:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) { throw 'Configuration check failed' }
Start-Service openssh-cygwin
.\bin\cygrunsrv.exe -VQ openssh-cygwin
Get-Content .\var\log\sshd.log -Tail 10
```

Allow the chosen TCP port through the firewall for the required sources.
For timeouts, follow the [service and listening-port checks](troubleshooting.md#connection-timeout-check-the-service-and-listening-port).
Before exposing any listening port, configure **AllowUsers** with the exact
accounts you intend to admit, using the SYSTEM configuration procedure below.
Without it, any otherwise eligible Cygwin account with an accepted key may log
in, including domain accounts. The defaults include a commented hardening
example for AuthenticationMethods publickey, MaxAuthTries 3, LoginGraceTime 30
and AllowUsers. Replace the account placeholder before enabling it. Keep an
existing tested administrator in the list while adding accounts.
Verify host keys through a trusted channel and save them on the client.
Then connect, for example, with
`ssh -o StrictHostKeyChecking=yes -p 2222 Administrator@server.example`.
Check key authentication, password rejection, TTY, exit codes and SFTP with hash comparison.

The default configuration disables passwords, keyboard-interactive authentication
and X11. SFTP runs internally; shells and commands use Cygwin Bash. Win32 OpenSSH
registry settings for the default shell do not apply here. Bash scripts need LF
line endings. Convert your own CRLF scripts with `sed -i 's/\r$//' file.sh` if needed.

SCP/SFTP paths use Cygwin syntax: `server.example:/cygdrive/c/Temp/file`,
instead of Windows OpenSSH's `/C:/Temp/file`. Commands run through Bash;
use `powershell.exe -File C:/Temp/task.ps1` with forward slashes, or
`powershell.exe -NoProfile -EncodedCommand <UTF-16LE-Base64>` to avoid nested
quoting. For complex Bash commands, transfer an LF .sh file and execute it
with the explicit PATH export rather than nesting several quote layers.

## Edit SYSTEM-owned configuration

After setup, sshd_config may be unreadable even to administrators. For changes
such as LogLevel or AllowUsers, use a protected copy made with
Robocopy /B /COPY:DAT. Preserve the original file's owner and ACL.
In elevated PowerShell:

```powershell
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$Edit = Join-Path $Root ('var\backups\config-' + [guid]::NewGuid().ToString('N'))
$Original = Join-Path $Edit 'original'
$Changed = Join-Path $Edit 'changed'
New-Item -ItemType Directory -Path $Original,$Changed -Force | Out-Null
icacls.exe $Edit /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Could not protect the backup directory' }
robocopy "$Root\etc" $Original sshd_config /B /COPY:DAT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Backup failed' }
Copy-Item "$Original\sshd_config" "$Changed\sshd_config"
$Before = (Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl
Start-Process notepad.exe -ArgumentList ('"' + "$Changed\sshd_config" + '"') -Wait
$Text = [IO.File]::ReadAllText("$Changed\sshd_config").Replace("`r`n","`n")
[IO.File]::WriteAllText("$Changed\sshd_config", $Text, (New-Object Text.UTF8Encoding($false)))
robocopy $Changed "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Copy back failed; retain the backup' }
if ((Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl -ne $Before) { throw 'Owner or ACL changed' }
& "$Root\bin\bash.exe" --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) {
    robocopy $Original "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
    if ($LASTEXITCODE -ge 8) { throw 'Restore failed; do not start the service' }
    throw 'Syntax error; original configuration restored'
}
Restart-Service openssh-cygwin
```

Backup mode needs elevated rights and available backup/restore privileges.
Keep the backup until functionality has been checked. Do not overwrite later
changes by restoring an old complete configuration.

## Restricting who may log in

Use exact Cygwin names returned by getent/id, including a local computer prefix
when present. The `+` in `MACHINE+Administrator` is literal and needs no escape.
For example, to keep only the local administrator:

```text
AllowUsers MACHINE+Administrator
```

To admit a domain account as well, resolve its name first. If getent identifies
it as `sshuser`, the checked multiple-directive form is:

```text
AllowUsers MACHINE+Administrator
AllowUsers sshuser
```

Replace both names with the actual passwd record names. A primary-domain user
may have an unqualified name; do not invent a domain prefix. Multiple global
AllowUsers directives append to the same list. Avoid a leftover broad pattern
which would admit an account you intended to exclude. DenyUsers, group rules,
Match blocks and other authentication requirements still need review.

Use the protected configuration workflow above. Keep an independent console
or management connection available, retain the original configuration, and
leave the current SSH session open where possible. A service restart can end
that session, so it cannot be your only recovery route. Run `sshd -t`, restart
the selected service, and test a **new** SSH connection before closing the
original session. If the test fails, use the independent console to restore
the protected backup with Robocopy /B /COPY:DAT, validate again and restart.
Automatic timed rollback tasks have not been validated by this procedure.

Test an admitted account and a deliberately unlisted account with a separately
verified valid key. Inspect `var\log\sshd.log` for the policy rejection.
An unlisted domain account with a valid key was rejected while the listed
local administrator continued to log in. TCP and SSH negotiation still occur;
AllowUsers is an authentication restriction, not a network connection filter.
After using install-user.cmd, inspect the global list and test the exact Cygwin
identity again; see NONADMIN-USERS.md for helper limitations.

### Limit SSH authentication by source address

The following IPv4 forms were checked with this Cygwin build. In the first
form, attach the address to the **exact** Cygwin username:

```text
UseDNS no
AllowUsers MACHINE+Administrator@192.0.2.10
```

CIDR and alternatives also worked, for example:

```text
AllowUsers MACHINE+Administrator@192.0.2.10 MACHINE+Administrator@198.51.100.0/24
```

These are alternatives, not cumulative requirements. A separate unrestricted
`AllowUsers MACHINE+Administrator` entry admitted the account despite another
address-restricted entry. Review the whole list rather than appending a
restriction beside an existing unrestricted entry.

The second form keeps the global user list and denies all users outside an
address list. Put global settings before the first Match block and place this
block at the end of sshd_config:

```text
AllowUsers MACHINE+Administrator
Match Address *,!192.0.2.10,!198.51.100.0/24
    DenyUsers *
```

Keep the leading `*` and the negated exceptions in the checked form. The listed source
was admitted; a source matching the deny block received
`Permission denied (publickey)`. The matching DenyUsers policy remained
effective despite the global AllowUsers entry. Neither form filters TCP before
the SSH exchange; check the authentication-policy reason in the server log.

Literal IP matching worked with UseDNS set to both no and yes. These examples
use numeric addresses; hostname-based access rules were not validated.
Behind NAT or a jump host, choose the source address recorded by sshd rather
than assuming it is the original client's address. NAT was used in the checks;
jump-host behavior still needs separate validation.
Use the same protected edit, syntax check, independent recovery connection
and second-session tests as for the account list.

### Windows Firewall as the first source filter

The firewall can prevent the SSH exchange from reaching sshd. An sshd rule
then provides an additional account/source restriction if a connection reaches
the daemon. Retain an independent administrative connection before changing
firewall rules; a second SSH session alone may also be blocked by the change.

The checked port-based rule form is:

```powershell
New-NetFirewallRule -Name OpenSSH-Cygwin-In-TCP -DisplayName 'OpenSSH Cygwin' -Direction Inbound -Protocol TCP -LocalPort 2222 -RemoteAddress 192.0.2.10 -Action Allow
```

Replace the port and source with your intended values. A remote-address list
was also checked, for example `-RemoteAddress 192.0.2.10,198.51.100.0/24`.
Inspect enabled inbound allow rules in the **ActiveStore**, including their
port/range, program and address filters. Review `OpenSSH-Server-In-TCP` and
any custom or policy-delivered rules which cover the chosen port. Another
broader allow rule can still admit traffic; adding a narrower allow rule does
not remove that broader permission. Restrict or remove only rules you have
identified and intend to change, preserving a recovery route and their
previous settings.

A rule tied to `%SystemRoot%\System32\OpenSSH\sshd.exe` did not admit this
installation in the check. Changing the test rule's program filter to the
actual `C:\Program Files\OpenSSH-Cygwin\usr\sbin\sshd.exe` admitted it again.
Use the port-based rule or the exact installed Cygwin executable path. Moving
the installation requires reviewing any program-based rule.

Test a new allowed connection and an excluded source. In the checked setup,
the excluded source timed out before receiving an SSH banner, while an sshd
account/address denial returned `Permission denied (publickey)`. A timeout
alone does not identify the cause: compare the effective rule/filter state,
the running listener and an allowed-source connection. Firewall drop logging
can provide additional evidence; enabling it was not part of these checks.

Before closing the recovery connection, restore the saved rule scope if the
allowed test fails and recheck a new connection. The test used an independent
management path while SSH was blocked. Automatic scheduled rollback and
different external clients/IPv6 were not validated; plan those separately.

## Logs and rotation

New registrations start sshd with `-D -E /var/log/sshd.log`; the file is
`var\log\sshd.log` in the installation tree. The default LogLevel is INFO.
OpenSSH's -E file output has no per-line timestamp in this build. Correlate
service starts/exits with timestamped Service Control Manager events in the
Windows System log. SyslogFacility applies to syslog/event routing when -E
is removed from the service arguments; changing SyslogFacility alone does not
timestamp the -E file. Event message rendering depends on the installed event
source. Do not assume those messages are complete without testing the route.
Use the configuration procedure above to enable VERBOSE. For manual rotation,
run elevated PowerShell inside the installation directory:

```powershell
$Log = Join-Path (Get-Location) 'var\log\sshd.log'
Stop-Service openssh-cygwin -ErrorAction Stop
try {
    if (Test-Path -LiteralPath $Log) {
        Move-Item -LiteralPath $Log -Destination ($Log + '.' + (Get-Date -Format 'yyyyMMdd-HHmmss')) -ErrorAction Stop
    }
} finally { Start-Service openssh-cygwin }
```

Check the new log file and permissions afterwards. For automatic rotation,
create an administrative maintenance job with error handling and a retention policy.

## Update

1. Verify the new ZIP and extract it to a new directory writable only by
   administrators. Keep the old tree. Save the service registration using
   the old `bin\cygrunsrv.exe -VQ openssh-cygwin`.
2. Stop your service. Back up etc, home, logs and your own data to an NTFS
   destination: `robocopy <source> <destination> /E /B /COPYALL /DCOPY:DAT /R:1 /W:1`.
   Exit codes of 8 or higher indicate failure. Restrict the backup to Administrators/SYSTEM.
3. Transfer active configurations, all private/public host keys and homes to
   the new tree with the same /B and /COPYALL options. Do not replace active
   configurations with templates. Compare the NSS home setting and new templates
   separately. Check host key counts, hashes, owners and permissions without
   displaying private contents.
4. Remove the stopped service using the **old** `bin\cygrunsrv.exe -R openssh-cygwin`.
   In the new directory, run `.\install-server.cmd --yes --name openssh-cygwin`.
   Add `--port` only when changing the port.
5. Check `sshd -t` with the PATH prefix shown above. Start the service and check
   its new registration, log file, unchanged host key fingerprints, login,
   exit codes and SFTP. Delete the old tree only after validation.

`/B` allows private host keys readable only by SYSTEM to be copied. Do not
continue with incomplete data when backup rights are missing or copying fails.
To roll back, stop/remove the new service, restore the old tree with its saved
data and permissions, and recreate its service registration.

## Migrate from Windows OpenSSH

Keep an independent administrative console or management path throughout the
change. First run this service on a different port, restrict its firewall rule,
set AllowUsers and test authentication, permissions, transfers and automation.
Check the new host-key fingerprint through the trusted management path:

```powershell
.\bin\ssh-keygen.exe -lf .\etc\ssh_host_ed25519_key.pub
```

If the new server uses different keys, compare the fingerprint before updating
the client's known_hosts entry. Do not bypass host-key checking.

Prepare the final port using the protected configuration workflow, with the
Cygwin service stopped. Keep the Windows service's previous startup mode and
working configuration available. Before cutover, schedule a SYSTEM rollback
task for about ten minutes later: stop and disable the Cygwin service, restore
the Windows service's previous startup mode and start it. Ensure the rollback script and
any saved configuration are writable only by Administrators/SYSTEM.

Use a separate SYSTEM task or the independent console for the cutover:
`Stop-Service sshd`, `Set-Service sshd -StartupType Disabled`, then
`Start-Service openssh-cygwin`. Stopping Windows sshd can end the SSH session
that requested it. Do not run both services on the same address/port. Confirm
the new service from another connection, including host identity and account
permissions, before cancelling the rollback task. Keep the fallback until
reboot startup has also been checked. These task names and service names must
be adapted to the installations you control.

## NTFS permissions and removal

Cygwin maps POSIX permissions to NTFS ACLs; NULL SID deny entries and None
group entries can be part of that mapping. Do not run a blanket recursive
icacls /reset. Save DACLs with icacls /save before repairs; it does not save
owners. Repair only affected paths you control, preserving host keys and StrictModes.

To remove the service, run as Administrator inside the installation directory:

```powershell
.\bin\cygrunsrv.exe -E openssh-cygwin
.\bin\cygrunsrv.exe -R openssh-cygwin
```

Check exit codes. Delete the installation tree and its firewall rule only after
successful service removal. User profiles and runtime limitations are covered
in TROUBLESHOOTING.md.

References: [Cygwin permissions](https://cygwin.com/cygwin-ug-net/ntsec.html),
[icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls),
[Robocopy](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy).

Access-rule references: [sshd_config(5)](https://man.openbsd.org/sshd_config.5),
[New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule).
