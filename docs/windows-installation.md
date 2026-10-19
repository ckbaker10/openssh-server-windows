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
Verify host keys through a trusted channel and save them on the client.
Then connect, for example, with
`ssh -o StrictHostKeyChecking=yes -p 2222 Administrator@server.example`.
Check key authentication, password rejection, TTY, exit codes and SFTP with hash comparison.

The default configuration disables passwords, keyboard-interactive authentication
and X11. SFTP runs internally; shells and commands use Cygwin Bash. Win32 OpenSSH
registry settings for the default shell do not apply here. Bash scripts need LF
line endings. Convert your own CRLF scripts with `sed -i 's/\r$//' file.sh` if needed.

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
