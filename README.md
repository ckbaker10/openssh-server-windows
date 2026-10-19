# OpenSSH Server for Windows

A standalone **OpenSSH 10.6p1 package for Windows x86_64**, including the
Cygwin runtime, Bash, SCP and SFTP. It provides remote access and file transfers
using SSH keys, including support for restricted Windows accounts.

The project provides a package that can be built on Linux and installed or
updated independently of the optional Windows OpenSSH feature. No Microsoft
SDK is required. The service runs as LocalSystem; signed-in users receive
their own Windows account permissions. Password authentication is disabled
by default. Releases are currently prereleases.

## Install as an administrator

Download the Windows ZIP and `SHA256SUMS` from [Releases](https://github.com/ckbaker10/openssh-server-windows/releases),
compare the ZIP hash, and extract it to `C:\Program Files\OpenSSH-Cygwin`.
`install-server.cmd` must be directly inside that directory.
Open **64-bit PowerShell as Administrator**:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -File .\verify-package.ps1
.\install-server.cmd --yes --name openssh-cygwin --port 2222
.\open-shell.cmd
```

In the Bash shell, add your own **public** key:

```bash
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME" "$HOME/.ssh"
cat >> "$HOME/.ssh/authorized_keys" <<'KEY'
ssh-ed25519 AAAA...replace_with_your_own_public_key
KEY
chmod 600 "$HOME/.ssh/authorized_keys"
exit
```

Back in PowerShell, check the configuration and start the service:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
Start-Service openssh-cygwin
```

Allow the chosen TCP port through the firewall for the required sources.
Connect from a client with `ssh -p 2222 Administrator@server.example`.
For keys, SYSTEM-owned configuration, logs and updates, see the
[installation guide](docs/windows-installation.md).

## Set up an unprivileged user

Use an existing, enabled **local Windows account without administrator rights**
and its public key file. An administrator performs the initial setup;
the subsequent SSH session remains restricted:

```powershell
.\install-user.cmd sshuser 'C:\Keys\sshuser.pub' -Start
```

The helper checks the account and SID, creates a new `/home/sshuser`, sets
ownership and permissions, and extends an existing global `AllowUsers` list.
Existing home directories are not overwritten. `-Start` starts the service
after success even if it was previously stopped.
Connect with `ssh -p 2222 sshuser@server.example`.
See [setting up and removing users](docs/nonadmin-users.md).

## Build from source

[COMPILE.md](COMPILE.md) covers the Linux cross-build with rootless Podman,
inputs, checks and output archives.
For known Cygwin limitations and diagnosis, see [troubleshooting](docs/troubleshooting.md).
