# Set up unprivileged users

The SSH service remains LocalSystem. An administrator runs `install-user.cmd`
to prepare an existing Windows account for restricted SSH sessions.
It does not create Windows accounts or change groups or passwords.

## Requirements

- An enabled local account without administrator rights; the built-in
  Administrator and Guest accounts are rejected.
- Exactly one OpenSSH public key file, without private data or authorized_keys options.
- A new Cygwin home `/home/<username>` as specified by nsswitch.conf.
  Existing homes are rejected before changes and are never overwritten.
- Elevated 64-bit PowerShell and available Robocopy backup mode privileges.

Account names may contain 1-20 ASCII letters, digits, `_`, `.` or `-`, must
start with a letter or digit, and must not end with a dot. The helper does
not support domain accounts or alternative home paths.

If needed, create the account through Windows first, for example:

```powershell
$Password = Read-Host 'Password for the new Windows account' -AsSecureString
New-LocalUser -Name sshuser -Password $Password
Remove-Variable Password
```

Do not add it to an administrator group. The password is not used for the
intended SSH key authentication; password authentication remains disabled.

## Run the helper

In elevated PowerShell, inside the installation directory:

```powershell
.\install-user.cmd sshuser 'C:\Keys\sshuser.pub' -Start
```

For another service name, add `-ServiceName <name>`. Its registration must
belong to this installation directory and run as LocalSystem. A running
instance is stopped during setup, so use a console that does not depend on
this SSH service staying available.

| Option | Behavior after successful setup |
| --- | --- |
| no start option | Restart a previously running service; leave a stopped service stopped |
| `-Start` | Always start the service, including after an earlier failed attempt |
| `-NoRestart` | Leave the service stopped |

`-Start` and `-NoRestart` cannot be combined. The final message explicitly
shows RUNNING or STOPPED. After STOPPED, you can run
`Start-Service openssh-cygwin` separately.

## Changes and error recovery

The helper checks the Windows SID, Cygwin account record, home and groups.
It validates the public key with ssh-keygen. Only the home, .ssh and
authorized_keys are created, assigned to the user's SID with icacls and set
to 700/700/600. Users can edit their own authorized_keys to add keys later.

An existing global AllowUsers list is extended without an identical duplicate.
If none exists, no new list is created. Match blocks remain untouched;
global Includes and quoted/escaped AllowUsers patterns require manual review.
DenyUsers, DenyGroups, AllowGroups and other rules remain effective.

The SYSTEM-owned configuration is backed up with Robocopy /B /COPY:DAT to
a protected `var\backups\user-<UTC>-<ID>` directory. Its owner and ACL must
remain unchanged when copied back. Before creating the home, the helper runs
`sshd -t` with an explicit Cygwin PATH. For manual configuration edits, follow
INSTALLATION.md; direct access by an administrator may fail.

If an error occurs after changes begin, the helper stops the service and tries
to restore the original configuration. It does not start the service afterwards.
Any newly created home is retained for inspection. Review the backup,
configuration, ownership and permissions before restarting. Remove a stale
`var\run\install-user.lock` only when no setup process is still running.

## Check restricted access

Verify host keys through a trusted channel first, then connect from a client:

```bash
ssh -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i ~/.ssh/userkey -p 2222 sshuser@server.example 'id; printf "HOME=%s\n" "$HOME"'
scp -P 2222 -i ~/.ssh/userkey file sshuser@server.example:file
```

Expected: /home/sshuser, no Administrators group, Medium Mandatory Level and
Admin=False when checking the PowerShell token. Writing to Windows system
directories, reading private host keys/sshd_config and controlling the service
should be denied. Check TTY, exit codes and file transfers with hash comparison;
password authentication must still be rejected.

## Remove an account

During an administrative maintenance window, record the exact SID before
deletion/reboot, disable the account and stop your service:

```powershell
$Name = 'sshuser'
$Sid = (Get-LocalUser -Name $Name).SID.Value
$Sid
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$UserHome = Join-Path (Join-Path $Root 'home') $Name
Disable-LocalUser -Name $Name
Stop-Service openssh-cygwin
```

End the account's sessions. Remove its keys and update any AllowUsers list
through backup mode. Do not overwrite later changes with an old complete
configuration. Removing the last AllowUsers entry must not accidentally
remove the entire restriction.

Only after verifying the exact home path you control and ensuring it contains
no reparse points:

```powershell
icacls.exe $UserHome /setowner '*S-1-5-32-544' /t /c
if ($LASTEXITCODE -ne 0) { throw 'Ownership change failed' }
icacls.exe $UserHome /grant '*S-1-5-32-544:(OI)(CI)F' /t /c
if ($LASTEXITCODE -ne 0) { throw 'Permission change failed' }
Remove-Item -LiteralPath $UserHome -Recurse -Force
Remove-LocalUser -Name $Name
```

Check configuration syntax with the PATH prefix in INSTALLATION.md, then start
the selected service. Windows profiles may remain loaded; follow
TROUBLESHOOTING.md before removing profiles. Do not force hive unloading.
