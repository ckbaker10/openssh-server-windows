# Package and Windows acceptance tests

Run tests from the repository root. The runtime ZIP contains `OpenSSH-Cygwin/`
and no test suite. The corresponding source tarball contains the project,
including this file and every script below, under `project/`.
Extract that directory to repeat the checks. Dependency source archives and
the signed Cygwin index remain at the source tarball's top level.

## Record the candidate

Build as described in [COMPILE.md](COMPILE.md). Keep the candidate ZIP, its
SHA-256, source commit, `build/inputs.lock.json`, builder image ID and tool
versions with each run. Record host `date +%s` before and after commands and
their real exit status. Put raw logs, VM disks, private test keys and temporary
credentials only beneath ignored `work/`. Never commit those files.
`tests/evidence.py` records exact argv, tool versions, input SHA-256 hashes,
host `date +%s` times, exit status and separate stdout/stderr logs. For example:

```sh
python3 tests/evidence.py --output work/checks/regression \
  --input dist/openssh-10.6p1-cygwin-x86_64.zip \
  --tool-version "$(python3 --version)" -- python3 -m unittest discover -s tests -v
```

Use a fresh output directory for each attempt. Arguments and version labels
must not contain passwords, private key contents or authentication headers.
Rebuilding after documentation changes produces another ZIP hash; compare
runtime payload hashes and identify which ZIP was used for native execution.

## Linux checks

The ZIP check extracts the actual delivery into `work/zip-check/OpenSSH-Cygwin`.
Run it before tests which exercise the packaged `ssh-host-config`:

```sh
python3 scripts/inputs.py fetch
podman run --rm --name openssh-server-windows-check \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 tests/check-package.py
python3 -m unittest discover -s tests -v
shellcheck -S warning scripts/*.sh packaging/*.sh tests/*.sh
hadolint build/Containerfile build/Containerfile.wine
podman run --rm --name openssh-server-windows-powershell-check \
  -v "$PWD:/project:Z" mcr.microsoft.com/powershell:lts-ubuntu-22.04 \
  pwsh -NoProfile -File /project/tests/check-powershell.ps1
podman run --rm --name openssh-server-windows-user-check \
  -v "$PWD:/project:Z" mcr.microsoft.com/powershell:lts-ubuntu-22.04 \
  pwsh -NoProfile -File /project/tests/check-user-setup.ps1
podman run --rm --name openssh-server-windows-wine-smoke \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-wine:10.6p1 \
  bash tests/smoke-wine.sh
```

`check-package.py` checks the sole ZIP root, CRCs, Windows filenames, runtime
directories, absence of manuals/private host keys/tests, complete manifest,
payload checksums, DLL imports and defaults. It also checks that every current
test file and this guide occur in the source tarball.
Python regressions exercise installer arguments, port selection, ownership
fallbacks, config preservation and Windows archive names. The Linux PowerShell
tests check the verifier and user-helper policy with simulated Windows APIs.
Wine covers the executable versions, key generation, Bash and `sshd -t`.
Neither mocks nor Wine establish native Windows acceptance.

## Disposable Windows guests

Use an isolated Windows member and Windows Server domain controller, with an
administrative management path independent of the SSH service under test.
Never point the acceptance scripts at an existing operational installation:
they create test accounts, replace `sshd_config`, restart the test service and
change their own TCP 2222 firewall rules. Use a checkpoint to restore the lab.

`tests/windows/vm.py` can create private writable overlays from **read-only,
standalone qcow2 checkpoints** of already installed Windows guests. Each
checkpoint must have matching `OVMF_VARS.fd`, `tpm/` and owner-only
`credentials.json` containing `username` and `password`. It does not install
Windows. Obtain evaluation media and accept applicable licenses separately;
no Windows images or credentials are distributed here.
The guest prerequisites are Windows PowerShell 5.1, administrative encrypted
NTLM WinRM, enabled backup/restore privileges, and AD DS/DNS management tools
on the test server. Preparing those prerequisites from a fresh Windows ISO is
not validated by this suite.

The KVM helper uses Ubuntu OVMF with Secure Boot, TPM 2.0, 4 vCPUs and 8 GiB per
guest. NAT forwards bind only to loopback: WinRM 56985/56986 and client SSH
57222 to guest 2222. HTTPS management uses 57985/57986 to guest 5986.
The second NIC connects only the two guests over a private
QEMU socket on loopback 56990. Preserve the checkpoint NIC identities and use
private addresses with a /24 prefix. Start the server first. Check these ports
are available; do not stop an unrelated process to take a port.

```sh
python3 tests/windows/vm.py clone server --source /path/to/server-checkpoint
python3 tests/windows/vm.py clone client --source /path/to/client-checkpoint
python3 tests/windows/vm.py start server
python3 tests/windows/vm.py start client
python3 tests/windows/vm.py status server
python3 tests/windows/vm.py screen client
```

`start` uses a separate user systemd unit, so the guests outlive a terminal or
controller interruption. It prints the unit name. `status` only establishes
that QEMU runs; verify Windows through WinRM. `screen` saves the actual guest
screen as PPM beneath `work/`. `powerdown` requests a normal guest shutdown;
wait for its recorded QEMU PID to exit before stopping that exact printed
unit to clean up its TPM process. Do not use broad process/container cleanup.

## Configure the native runner

Use Python with `tests/windows/requirements.txt` installed in an isolated
environment; pywinrm 0.5.0 was used. Set `OPENSSH_TEST_ROOT` to the ignored lab
directory. Copy `tests/windows/config.example.json` there as `config.json` and
replace the example hostnames and addresses with the **test** values. The
client and server credentials remain in their separate 0600 files; the
configuration contains no passwords. The controller uses encrypted NTLM
messages even when the loopback WinRM transport uses HTTP.
Set `domain_test_user` to an existing enabled account in the disposable domain,
with a Cygwin home dedicated to this run. The allow-list test installs a new
public test key for it. Optional `create_domain_test_user: true` attempts to
create that account through a SYSTEM task on the domain controller; this
provisioning path has not completed validation and is disabled by default.

For example, an isolated controller environment can be prepared with uv:

```sh
uv venv --python python3 work/windows-env
uv pip install --python work/windows-env/bin/python -r tests/windows/requirements.lock
. work/windows-env/bin/activate
```

`source_address` is the address actually seen by sshd, not necessarily the
controller's physical address. With the supplied QEMU NAT forwarding it is
normally `10.0.2.2`; verify it in the server log. Set `denied_source` to a
different documentation-only address. The two private guest addresses are
for the isolated AD link; they are independent of this NAT source address.

```sh
export OPENSSH_TEST_ROOT="$PWD/work/windows-lab"
python tests/windows/lab.py client tests/windows/status.ps1
python tests/windows/lab.py server tests/windows/status.ps1
```

The status output records OS, build and domain membership. Transport failures
are failures, not passes. Do not publish their private logs without review.
The suite retains a WinRM shell and its user registry hive for the complete
controller run, including operations performed by CIM/COM providers. This is
separate from PowerShell's `-NoProfile` switch, which suppresses profile scripts.
Run the acceptance matrix in one controller process. If Windows reports a
registry key marked for deletion or a broken CIM session, preserve the error
and restart only the disposable guest with `restart.ps1`; do not force-unload
registry hives or change global profile settings.
For that recovery command, `OPENSSH_TEST_NO_PROFILE=1` avoids loading the
affected user hive. Recheck readiness through a fresh controller after reboot.

## Prepare and join the isolated domain

Skip promotion for a checkpoint that already contains the intended lab domain.
The forest script refuses a second promotion. For a new forest, use
an administrative account whose known test password will remain valid after
promotion. Set `domain_admin_name` to that account's name (default:
Administrator); the runner qualifies it with the test domain after promotion.
Keep the recovery password generated by the controller private. If the
promotion completed but its management response was interrupted, verify the
domain state before using `domain.py domain-identity` to update that username.

```sh
python tests/windows/domain.py mark
python tests/windows/domain.py clock
python tests/windows/domain.py promote
# Wait for the planned server reboot and verify WinRM again.
python tests/windows/lab.py server tests/windows/status.ps1
python tests/windows/domain.py join
# Wait for the planned client reboot, then verify domain membership.
python tests/windows/wait.py client
python tests/windows/lab.py client tests/windows/status.ps1
```

The scripts configure only the lab's private NICs, DNS and test forest. Keep
the client's WinRM credentials explicitly machine-qualified when it joins.
Clock setting can invalidate an active management connection; verify the guest
state through a new connection before repeating a mutation.

## Enable HTTPS management

For the acceptance run, enable HTTPS management and pin the public guest
certificate. The helper creates a 30-day localhost certificate with an
IP subject alternative name for 127.0.0.1, configures only the lab listener
and a source-scoped management firewall rule, saves the public certificate,
and updates that guest's URL and trust path in the private config.
It never exports the private certificate key or disables certificate checks:

```sh
# Existing VMs started without the HTTPS forwards:
python3 tests/windows/vm.py https-forward client
python3 tests/windows/vm.py https-forward server
OPENSSH_TEST_NO_PROFILE=1 python tests/windows/enable-https.py client
OPENSSH_TEST_NO_PROFILE=1 python tests/windows/enable-https.py server
OPENSSH_TEST_NO_PROFILE=1 python tests/windows/lab.py client tests/windows/status.ps1
```

VMs started by the current `vm.py` already have these forwards; do not add
them twice. Keep the original encrypted HTTP endpoint available until the
HTTPS endpoint passes certificate validation. HTTPS protects the NTLM
exchange and test scripts without relying on HTTP message-encryption state
across long-running task operations.

## Install and exercise the candidate

Serve the candidate `dist/` directory to the owned NAT guests, bound to
loopback on the host, and set `archive_url` accordingly. Keep this server alive
while downloading. The supplied `setup.ps1` extracts into `C:\Program Files`,
checks the package and installs only `openssh-cygwin-test` on TCP 2222.
It enables and assigns a random test password to the local Administrator.
The verifier invocation bypasses execution policy only for that process;
no machine-wide execution policy is changed.

```sh
python3 -m http.server 57380 --bind 127.0.0.1 --directory dist
# In the separate controller terminal:
python tests/windows/acceptance.py status
python tests/windows/acceptance.py setup
# Before joining, optional standalone baseline:
python tests/windows/standalone.py
# After joining/rebooting, run all acceptance phases in one controller:
python tests/windows/run-suite.py --phases auth,local-admin-recipe,allow,transfers,source,firewall,userhelper
```

For a fresh joined member without an installation, add `setup,` before `auth`.
Individual phase scripts are available for diagnosis; use a clean guest state
and preserve the result of failed attempts before retrying. `run-suite.py`
checks the domain secure channel and stops at the first failing phase.

The account test records both Administrator passwd entries, assigns
700/700/600 and ownership to the local UID, tests the qualified login and
records the unqualified and nonexistent-account outcomes with the server log.
The allow-list test first proves a separate domain account has a valid key,
then excludes it and admits it again through a second `AllowUsers` directive.
Transfers test allowed and rejected SCP/SFTP and compare the SFTP roundtrip bytes.
Source tests cover an exact address, CIDR, address alternatives, UseDNS, an
unrestricted user entry beside a restricted one, and both Match outcomes.
Firewall tests inspect effective profiles/rules, deny the same source by
changing its scope, admit an address list, and compare the Windows OpenSSH
program path with this package's actual `usr\sbin\sshd.exe` path.
The user-helper test prepares a new local non-administrator, inspects the
updated global allow-list, and attempts both short and qualified logins.
If it fails during preflight, `userhelper-diagnose.py` records the Windows
account state, short/qualified Cygwin lookup results and preserved allow-list.
`manual-user.py` separately checks manual qualified-account preparation,
token groups and SCP/SFTP, refusing an existing home. `source-extra.py` checks
a Match CIDR exemption and the reverse ordering of user/address entries.

Some checks intentionally fail a client request. They count as passes only
when the expected rejection is observed; retain the client result and matching
server log. No timeout proves account-level rejection. Initial connection
attempts may require a bounded longer startup allowance; preserve every failed
attempt instead of silently retrying an entire command with side effects.
The client wrapper permits one delayed reconnect only after an SSH banner
timeout, before authentication or any remote operation starts. Every attempt
has its own logs. Account-policy tests require an explicit public-key denial;
network timeouts cannot pass an authentication-denial test.

The runner uses temporary SYSTEM tasks for operations on SYSTEM-owned files.
Guest task scripts and logs stay in protected `C:\openssh-checks`. Complex Bash
commands are written as LF scripts and executed by filename with an explicit
Cygwin PATH. Host results have separate run directories with command argv,
script hashes, stdout/stderr, exit codes and host times. Private keys stay
outside the source archive and ZIP.

## Verify the final repack

Keep the ZIP actually used for native installation. If only documentation was
changed afterwards, `compare-runtime.py` proves every other payload byte and
the runtime file list stayed unchanged:

```sh
python3 tests/compare-runtime.py work/windows-lab/tested-package-complete.zip dist/openssh-10.6p1-cygwin-x86_64.zip
OPENSSH_TEST_NO_PROFILE=1 python tests/windows/verify-candidate.py dist/openssh-10.6p1-cygwin-x86_64.zip
```

The native final-candidate check downloads the configured archive URL, compares
its SHA-256 with the host ZIP, extracts into a separate temporary directory,
checks the `OpenSSH-Cygwin` root and test exclusions, and runs the supplied
verifier under Windows PowerShell 5.1. It does not execute another Cygwin tree
or replace the running installation. Re-run `tests/check-package.py` after the
last archive build; it also compares every bundled project source file with
the source actually checked, so stale test scripts cannot pass unnoticed.

## Acceptance status

Linux package, Python regression, PowerShell helper and Wine checks passed for
the initial candidate. Native Windows 11 build 26300 installation, SYSTEM
owners, syntax check and standalone local Administrator key login passed.
Windows Server 2025 build 26100 was used for the isolated domain controller.
The following native checks passed on the Windows 11 domain member:

| Check | Result |
| --- | --- |
| Local/domain Administrator resolution and shared home | Distinct SIDs/UIDs, same home; qualified local key login passed |
| Unqualified Administrator and nonexistent account | Public-key denial; ownership and invalid-user log reasons recorded |
| AllowUsers with a proven domain key | Listed local user admitted; unlisted domain user denied |
| Multiple global AllowUsers directives | Both listed users admitted |
| Unrestricted and source-restricted entries, both orders | The unrestricted entry admitted the account |
| SCP and SFTP | Local user admitted, unlisted domain user denied; SFTP bytes matched |
| User@IP, CIDR, alternatives, UseDNS no/yes | Allowed and denied outcomes matched policy |
| Match Address exceptions plus global AllowUsers | Allowed and denied outcomes matched policy |
| Match CIDR exemption | The matching subnet was admitted |
| Windows Firewall remote scope and list | Excluded source timed out; allowed source connected |
| Windows OpenSSH vs Cygwin program path | Wrong path blocked; exact Cygwin path admitted |
| Manual qualified local non-administrator | No Administrators group; SCP/SFTP and roundtrip bytes passed |

The native install-user.cmd domain-member check **failed during preflight**:
the local base name did not resolve through Cygwin, while its machine-qualified
name did. No home or AllowUsers entry was created by the helper. This is a
recorded limitation, not a passing helper result; see NONADMIN-USERS.md.
Manual qualified non-administrator and additional source-order checks are
successful checks recorded separately from the failed helper attempt.

The reported abrupt connection close when offering a key for unqualified
Administrator was not reproduced; the checked member returned a public-key
denial with a bad-ownership diagnostic. Intermittent banner timeouts and a
failed service-start attempt were retained as failed attempts; no runtime fix
or connection-success rate is claimed.

Windows Server 2022 member behavior, AllowGroups, IPv6, legacy SCP (-O),
jump-host variations, firewall drop logging, automatic timed rollback and
the optional new-domain-user provisioning path require separate validation.
The source-scope tests changed policy for the same known NAT source rather
than using a second external machine. Keep these limits with the results.
