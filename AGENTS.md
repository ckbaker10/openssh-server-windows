# Repository instructions

## Build and packaging

Cross-build on Linux using rootless Podman only, without the Microsoft SDK.
Build and validation commands are in COMPILE.md. Verify build/inputs.lock.json;
update versions consistently across scripts, image tags, tests and documentation.
Never disable signature or hash checks. Store generated artifacts and raw
diagnostic data only in the ignored dist/ and work/ directories. Preserve
others' changes and stage only your own files explicitly.

Ship ZIPs without Man or Info pages, with Windows-compatible file names,
a complete manifest, SHA256SUMS and verifier. Retain license notices and the
installation, user and troubleshooting guides. Never package private keys,
passwords or private environment configuration.

## Installation

Support LocalSystem services only; reject unsupported account/password options
without exposing secrets. Keep default templates; --yes must not delete existing
configuration. Test explicit ports including 22. Set the SYSTEM ACL as group
g:18 and retain a visible, nonfatal warning on failure. Skip ownership changes
when the UID is already correct. Do not change NTFS permissions across the
installation root.

Every Bash invocation without profiles needs an explicit Cygwin PATH, either
inside the script or before the command. Check native exit codes using the
globally updated LASTEXITCODE. Edit configuration with Robocopy /B /COPY:DAT
while preserving ownership/ACLs; document /B /COPYALL for backup and migration.

install-user.cmd supports existing, enabled local non-administrator accounts
with a new /home/NAME. Do not overwrite existing homes or change accounts,
passwords or groups. Check SID, groups, keys, 700/700/600 and global AllowUsers.
Do not change Match blocks; require manual review for Include and complex patterns.
Control only this installation's service. Restore configuration after a failed
mutation and leave the service stopped. -Start and -NoRestart are mutually exclusive.

## Validation and releases

Run shellcheck -S warning on changed shell scripts before every commit.
Run package, DLL, version, regression, PowerShell and Wine checks before release.
Do not describe Windows mocks or Wine as native Windows validation. State the
limits of new script paths; publish prereleases until validation is complete.
Commit and push your verified changes. Use new release tags and assets;
never replace published tags or assets. Existing release titles and descriptions
may be translated when requested, while preserving flags, tags and asset hashes.

Keep all public documentation and release descriptions in English and portable:
no private hostnames, absolute workspace paths, operations reports, automation
plans or test environments. Keep README short, with the purpose and both setup
paths; put build details in COMPILE.md. Describe general runtime limitations in
docs/troubleshooting.md. Do not make unverified profile, hive or global PATH
changes, or modify other people's systems.
