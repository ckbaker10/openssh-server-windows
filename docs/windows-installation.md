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

Extract to `C:\Program Files\OpenSSH-Cygwin`, renaming the outer ZIP directory
if needed. `install-server.cmd` and `bin\cygwin1.dll` must be directly beneath
that directory. Only Administrators and SYSTEM should be able to modify this
installation tree. Then verify it in PowerShell:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -File .\verify-package.ps1
```

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
