# Troubleshooting and Cygwin limitations

## Connection timeout: check the service and listening port

Run these checks **on the Windows SSH server**, in elevated 64-bit PowerShell.
Use your actual service name if it differs from `openssh-cygwin`:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
Get-Service -Name openssh-cygwin
sc.exe qc openssh-cygwin
sc.exe queryex openssh-cygwin
Get-NetTCPConnection -State Listen |
    Where-Object { $_.LocalPort -in 22,2222 } |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

A missing service means this name is not registered. Check the name and
installation result before running setup again. `Running` alone does not prove
that SSH is listening. No listener rows means neither port is currently
listening; a remote timeout alone cannot distinguish this from a firewall drop.
Port 2222 is the setup example; a new configuration without `--port` uses 22.
Existing configurations can use another port.

Check the registered executable and arguments with `sc.exe qc` and identify
the listener's process with `Get-Process -Id <OwningProcess>`. Another SSH
installation may own port 22. Check `Port` and `ListenAddress` in
`etc\sshd_config`, any included files, and service command-line overrides.
For another port, repeat the listener query with that port. A listener bound
only to `127.0.0.1` or `::1` cannot accept connections to the server's LAN
address. Check the address family and interface as well as the port.

If stopped, first check configuration and then start this service:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) { throw 'Configuration check failed' }
Start-Service -Name openssh-cygwin -ErrorAction Stop
Get-Service -Name openssh-cygwin
Get-NetTCPConnection -State Listen |
    Where-Object { $_.LocalPort -in 22,2222 } |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Run the checks separately and inspect errors before continuing. If configuration
access is denied, follow [Cannot read SYSTEM-owned configuration](#cannot-read-system-owned-configuration)
and the ownership checks in INSTALLATION.md. Do not loosen the installation
tree's permissions. A successful interactive `sshd -t` does not prove that
the service can start under SYSTEM.

If startup fails, the service stops again, or no expected listener appears,
collect the exit status and recent logs:

```powershell
sc.exe queryex openssh-cygwin
Get-Content .\var\log\sshd.log -Tail 80
Get-WinEvent -FilterHashtable @{
    LogName = 'System'
    ProviderName = 'Service Control Manager'
    StartTime = (Get-Date).AddMinutes(-15)
} -MaxEvents 50 | Select-Object TimeCreated,Id,LevelDisplayName,Message
```

Correlate events for this service with the attempted start time. Preserve the
exact start error and relevant log lines; an absent log is also useful evidence.
Share only redacted diagnostics and relevant configuration directives, never
private host keys, credentials or an entire installation directory.

Once the expected listener exists, test its actual bound address locally and
then from the intended client. Replace `server.example` and port 2222 below
with the server's LAN address or DNS name and the observed listening port:

```powershell
Test-NetConnection -ComputerName server.example -Port 2222
```

Check `TcpTestSucceeded`; ping success or failure does not establish SSH TCP
reachability. If the local TCP test succeeds but the remote test fails, inspect
Windows Defender Firewall with Advanced Security (`wf.msc`): the active network
profile, enabled inbound TCP rules, local port, allowed remote addresses,
program/service restrictions and blocking rules. Allow only the intended client
sources on the observed port; keep the firewall enabled. Also check intervening
network filters and the client's destination address. Reachable RDP or WinRM
does not prove that the SSH port is reachable, and a TCP connection alone does
not prove successful SSH authentication. Match the client's `Port` to the
verified listener before changing jump-host settings.

Command references: [Get-NetTCPConnection](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-nettcpconnection),
[Test-NetConnection](https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection),
and [Get-WinEvent](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent).
These diagnostic steps require validation on the affected Windows host.

## Exit code 127 from Bash

With --noprofile --norc, Bash inherits the translated Windows PATH. Add
/usr/bin, /bin and /usr/sbin for Cygwin programs and their dependencies:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
```

Put this export at the beginning of your own .sh files and use LF line endings.
No permanent change to the global Windows PATH is needed. The user helper
sets this PATH for its syntax check.

## Cannot read SYSTEM-owned configuration

After setup, sshd_config may be owned exclusively by SYSTEM and unreadable
to administrators. Copy it to a protected working directory using
Robocopy /B /COPY:DAT, edit it there, and copy it back with /IS /IT.
Check exit codes, preserve ownership/ACLs and run sshd -t before restarting.
The full procedure is in INSTALLATION.md. Keep StrictModes enabled.

## User helper leaves the service stopped

After a failed change, the configuration is restored and the service is left
stopped for inspection. Review the configuration and any newly created home.
Use `-Start` for a successful new setup attempt, or run
`Start-Service openssh-cygwin` afterwards. An existing home is not overwritten,
including after an earlier failed attempt.

## Local and domain Administrator share a home

With `db_home: /home/%U`, different Windows SIDs can resolve to the same home.
On the checked domain member, Administrator resolved to the domain account;
`MACHINE+Administrator` resolved to the local account. Inspect both passwd
records and the local account's `id` output before assigning keys or owners.
INSTALLATION.md describes the local administrator procedure.

With the home and authorized_keys owned by the local UID, the qualified local
login succeeded. The unqualified domain login was rejected with
`Permission denied (publickey)` and this server diagnostic:

```text
Authentication refused: bad ownership or modes for file /home/Administrator/.ssh/authorized_keys
```

A nonexistent account also produced `Permission denied (publickey)`; the
server identified it as an invalid user. Client authentication failure alone
does not prove that an account exists. Check getent/id and the server log.

A reported variation closes the connection when a key is offered for the
unqualified Administrator. That abrupt-close variation was **not reproduced**
on the checked Windows 11 member, and its cause remains unverified for Windows
Server 2022. Do not infer the same cause from the client message alone. Collect
the matching `var\log\sshd.log` section, the exact resolved account and numeric
owners; correlate fork/seteuid or service failures with Windows events if present.
Keep StrictModes enabled and do not change ownership of the installation tree.

## User helper reports Bash exit 2 on a domain member

An existing Windows local account may require a qualified Cygwin name even
when its base name is not present in the domain. In the checked case,
`getent passwd sshuser` returned exit 2 and `id sshuser` failed, while
`getent passwd 'MACHINE+sshuser'` and the corresponding id lookup succeeded.
The account was enabled and was not an administrator.

install-user.cmd requests the unqualified name during preflight, so it failed
before creating a home or changing AllowUsers. Inspect both lookups and the
local Windows SID; do not remove SID checks, administrator checks or home
protections to make setup continue. Qualified helper input is unsupported.
See NONADMIN-USERS.md for the current limitation and manual account guidance.

## Intermittent fork errors or dropped connections

`fork of unprivileged child failed` means that Cygwin could not create a child
process. The Cygwin FAQ lists DLL address-space conflicts and interference
from third-party software among possible causes. Collect server logs and
Windows events for the same time, check available memory and runtime version,
and investigate compatibility of installed security/hooking software.
The sshd message alone does not identify a specific cause.
[Cygwin: fork failures](https://cygwin.com/faq/faq.html#faq.using.fixing-fork-failures).

If a fork diagnostic includes `0xC0000142`, Windows defines this as
`STATUS_DLL_INIT_FAILED`: DLL initialization failed in the child process.
The code identifies neither the DLL nor the underlying cause. Record the
complete diagnostic and whether setup was running in an interactive or remote
session. DLL placement, injected software and session resources need evidence
before choosing a fix; do not rebase installed DLLs while processes use them.
[Microsoft: NTSTATUS values](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55).

Retry operations that are safe to repeat after an isolated failure; check
destination files and hashes after transfers. Do not blindly repeat commands
with unknown partial effects. MaxStartups controls concurrent unauthenticated
connections and is not a demonstrated fix for this fork error. Do not add
blanket antivirus exclusions or make global security changes.

Connection success rates can vary between runs with identical binaries.
For automation, allow one delayed reconnect for connection-establishment
failures, with a bounded timeout. An interrupted command may already have run;
verify its result before retrying it. `seteuid ... Permission denied` also
requires account/token diagnostics; it does not establish a DLL-rebase cause.

## Service stopped after reboot

Early connections during Windows startup can coincide with fork/seteuid
failures and an unexpected service exit. New installations use delayed
automatic startup and retain the TCP/IP dependency. Neither setting proves
that login/profile initialization is complete. Availability begins after the
startup phase; use a monitoring grace period and bounded backoff instead of
opening a connection every second from boot.

`Get-Service openssh-cygwin` can report Stopped even when its startup mode is
Automatic. Check the timestamped Service Control Manager events (including
7034), `sc.exe qc openssh-cygwin`, `sc.exe queryex openssh-cygwin` for exit
codes, and the full
sshd log before an administrative `Start-Service openssh-cygwin`.
See [Microsoft sc.exe config](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-config)
for delayed startup syntax. It is a mitigation requiring reboot validation.

In the shipped daemon source, a failed connection fork is logged, and a startup
pipe read error closes that child's state while the accept loop continues.
The final `startup pipe ... read Software caused connection abort` line does
not by itself identify why the service exited. Preserve adjacent Windows
events, exit status and, through an approved diagnostic procedure, a crash
dump if available. No daemon crash fix is claimed from these messages alone.

## Installer reports ownership warnings

The host-config exit code counts errors/warnings; service registration and
`sshd -t` can succeed despite an incorrect owner. The installer tries scoped
chown and icacls repairs and prints the affected file and failure. Verify SYSTEM
ownership of sshd_config and private host keys using the procedure in
INSTALLATION.md. An elevated SSH token may still lack effective owner-restore
rights; repair the exact file from a local administrative console or a controlled
SYSTEM task if necessary. Backup-mode config editing preserves an incorrect
owner until it is repaired explicitly. Do not dismiss a nonzero installer exit.

## Log entries have no timestamps

The -E sshd.log output has no per-line timestamps. Correlate it with the Windows
System log's Service Control Manager timestamps and record collection times.
Changing SyslogFacility does not add timestamps to -E output. The installation
guide describes the alternative event/syslog route and its rendering limits.

## First login returns no output

The first SSH command for a new account may finish with the expected exit code
but no output. Open a new connection and try a harmless diagnostic such as
`printf 'SSH output check\n'`. Check standard output, standard error and the exit
code separately. Do not repeat a command with side effects until its result has
been checked.

Windows profile initialization is a possible explanation, but the cause has
not been established. If the problem persists after the first login, collect
client diagnostics and the corresponding server log rather than treating it
as normal startup behavior.

## Windows profile remains loaded

A key-authenticated account's profile may remain loaded after its session
ends, the service stops or the account is deleted. In
`winsup/cygwin/sec/auth.cc`, load_user_profile documents a registry handle
that is retained for now and an open TODO for reliable profile unloading.
This does not establish a specific S4U token cause or measured memory growth.

Record the SID before deleting the account. After a planned reboot, use that
exact SID to check and remove only a profile that is no longer loaded:

```powershell
$Sid = '<previously recorded user SID>'
$Profile = Get-CimInstance Win32_UserProfile -Filter "SID='$Sid'"
$Profile | Select-Object SID,LocalPath,Loaded
if ($Profile -and -not $Profile.Loaded) { $Profile | Remove-CimInstance }
```

If Loaded=True, do not force removal: do not run reg unload or broadly delete
HKEY_USERS, ProfileList or profile directories. A runtime fix requires
reproducible handle/profile measurements and validation on Windows.

## PATH and tools in SSH sessions

Cygwin OpenSSH inherits parts of the service environment, including PATH.
This can include system profile paths or other SSH installations. Use absolute
paths or `command -v ssh` and `command -v powershell.exe` in scripts.
command -v is built into Bash; a separate which program is not required.
Setup changes neither the global PATH nor the default shell for other applications.

## Validation scope

Linux/Wine checks and simulated Windows interfaces do not replace native
Windows validation. Test new helper paths, service startup after reboot,
rollback, domain/additional groups, concurrent sessions, network shares and
Ansible separately. Key authentication may require additional Windows
authentication for network shares. Releases remain prereleases until
validation is complete.
