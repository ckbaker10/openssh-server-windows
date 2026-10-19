# Windows PowerShell 5.1 compatible. Native operations are isolated for testing.
Set-StrictMode -Version 2

function Assert-UserName {
    param([string]$Name)
    if ($Name -cnotmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,19}$' -or $Name.EndsWith('.')) {
        throw 'Use a local account name of 1-20 ASCII letters, digits, _, . or -, without a trailing dot.'
    }
}

function ConvertTo-PublicKeyLine {
    param([string]$Text)
    $lines = @($Text -split '\r?\n' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -ne 1 -or $lines[0].Trim() -cnotmatch '^([a-z0-9][a-z0-9@._+-]*)[ \t]+([A-Za-z0-9+/]+={0,2})(?:[ \t]+[^\r\n]*)?$') {
        throw 'Supply exactly one OpenSSH public key, without authorized_keys options or private key data.'
    }
    try { $null = [Convert]::FromBase64String($Matches[2]) } catch { throw 'Invalid public key encoding.' }
    return $lines[0].Trim() + "`n"
}

function Update-UserAllowList {
    param([string]$Text, [string]$Name)
    Assert-UserName $Name
    $lines = $Text.Replace("`r`n", "`n").Split([char]10)
    $indexes = @()
    $present = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $active = [regex]::Replace($lines[$i], '(^|\s)#.*$', '$1')
        if ($active -match '^\s*Match\s') { break }
        if ($active -match '^\s*Include\s') { throw 'Include configurations need manual review; no files were changed.' }
        if ($active -match '^\s*AllowUsers\s+(.+?)\s*$') {
            $patterns = $Matches[1]
            if ($patterns.Contains('"') -or $patterns.Contains("'") -or $patterns.Contains('\')) {
                throw 'Quoted or escaped AllowUsers patterns need manual review; no files were changed.'
            }
            $indexes += $i
            if (@($patterns -split '\s+') -ccontains $Name) { $present = $true }
        }
    }
    if ($indexes.Count -eq 0 -or $present) { return $Text }
    $index = $indexes[0]
    $comment = [regex]::Match($lines[$index], '\s+#')
    if ($comment.Success) {
        $lines[$index] = $lines[$index].Substring(0, $comment.Index).TrimEnd() + ' ' + $Name + $lines[$index].Substring($comment.Index)
    } else { $lines[$index] = $lines[$index].TrimEnd() + ' ' + $Name }
    return $lines -join "`n"
}

function Assert-LocalNonAdmin {
    param($Account, [object[]]$Administrators)
    if (-not $Account.Enabled -or $Account.SID.Value -match '-50[01]$') { throw 'Use an enabled local account other than built-in Administrator/Guest.' }
    if (@($Administrators | Where-Object { $_.SID.Value -eq $Account.SID.Value }).Count -gt 0) {
        throw 'The account is a member of Administrators; no files were changed.'
    }
    Assert-UserName $Account.Name
}

function Invoke-UserTool {
    param([string]$File, [string[]]$Arguments, [int[]]$SuccessCodes = @(0))
    $previousPreference = $ErrorActionPreference
    try {
        # Native commands update the global value; a local variable hides it.
        # PS 5.1 stderr records must not bypass the actual exit-code check.
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = $null
        $output = @(& $File @Arguments 2>&1)
        $code = $global:LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($null -eq $code) { throw ((Split-Path -Leaf $File) + ' could not be executed.') }
    if ($SuccessCodes -notcontains $code) { throw ((Split-Path -Leaf $File) + " failed (exit $code).") }
    return $output
}

function Copy-UserBackupFile {
    param([string]$Source, [string]$Destination, [string]$FileName)
    $null = Invoke-UserTool -File "$env:SystemRoot\System32\robocopy.exe" -Arguments @(
        $Source, $Destination, $FileName, '/B', '/COPY:DAT', '/IS', '/IT', '/R:0', '/W:0', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
    ) -SuccessCodes (0..7)
    if (-not [IO.File]::Exists((Join-Path $Destination $FileName))) { throw 'Backup-mode copy did not produce the required file.' }
}

function Assert-NoUserReparsePoint {
    param([string]$Path)
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Reparse points are not supported in setup paths.'
        }
    }
}

function Assert-UserAdministrator {
    if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitProcess) { throw 'Run in elevated 64-bit Windows PowerShell.' }
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run install-user.cmd from an elevated Administrator terminal.' }
}

function Install-OpenSshUser {
    [CmdletBinding()]
    param([string]$Root, [string]$Name, [string]$PublicKeyFile, [string]$ServiceName = 'openssh-cygwin', [switch]$NoRestart)
    $ErrorActionPreference = 'Stop'
    Assert-UserAdministrator
    Assert-UserName $Name
    if ($ServiceName -notmatch '^[A-Za-z0-9_.-]+$') { throw 'Invalid service name.' }
    $Root = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    foreach ($path in @($Root, (Join-Path $Root 'home'))) { Assert-NoUserReparsePoint $path }
    $account = Get-LocalUser -Name $Name -ErrorAction Stop
    Assert-LocalNonAdmin -Account $account -Administrators @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop)
    $Name = $account.Name
    $key = ConvertTo-PublicKeyLine ([IO.File]::ReadAllText([IO.Path]::GetFullPath($PublicKeyFile)))
    $userHome = Join-Path (Join-Path $Root 'home') $Name
    if ($null -ne (Get-Item -Force -LiteralPath $userHome -ErrorAction SilentlyContinue)) {
        throw 'The Cygwin home already exists. This helper only provisions new homes and never overwrites existing keys or data.'
    }
    $bash = Join-Path $Root 'bin\bash.exe'
    $record = @(Invoke-UserTool -File $bash -Arguments @('--noprofile', '--norc', '/install-user.sh', 'inspect', $Name))
    if ($record.Count -ne 1) { throw 'Cannot resolve one Cygwin account record.' }
    $fields = ([string]$record[0]).Trim().Split(':')
    if ($fields.Count -ne 7 -or $fields[2] -notmatch '^[1-9][0-9]*$' -or $fields[5] -cne "/home/$Name" -or
        $fields[4] -notmatch ('(?:^|,)' + [regex]::Escape($account.SID.Value) + '(?:,|$)')) {
        throw 'Cygwin SID/home does not match the local account and /home/NAME. Review NSS before setup.'
    }
    $service = Get-CimInstance -ClassName Win32_Service -Filter ("Name='$ServiceName'") -ErrorAction Stop
    $servicePattern = '^\s*"?' + [regex]::Escape((Join-Path $Root 'bin\cygrunsrv.exe')) + '"?(?:\s|$)'
    if (-not $service -or $service.PathName -notmatch $servicePattern -or $service.StartName -notin @('LocalSystem', 'NT AUTHORITY\SYSTEM')) {
        throw 'The selected LocalSystem service does not belong to this installation.'
    }
    if ($service.State -notin @('Running', 'Stopped')) { throw 'Wait until the selected service is running or stopped.' }
    $lockPath = Join-Path $Root 'var\run\install-user.lock'
    $lock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $backup = $null
    $configAttempted = $false
    $mutating = $false
    $wasRunning = $service.State -eq 'Running'
    try {
        $backup = Join-Path $Root ('var\backups\user-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N'))
        $null = [IO.Directory]::CreateDirectory($backup)
        $null = Invoke-UserTool -File "$env:SystemRoot\System32\icacls.exe" -Arguments @(
            $backup, '/inheritance:r', '/grant:r', '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F'
        )
        $original = Join-Path $backup 'original'
        $proposed = Join-Path $backup 'proposed'
        $null = [IO.Directory]::CreateDirectory($proposed)
        $keyPath = Join-Path $proposed 'authorized_keys'
        [IO.File]::WriteAllText($keyPath, $key, (New-Object Text.UTF8Encoding($false)))
        $null = Invoke-UserTool -File (Join-Path $Root 'bin\ssh-keygen.exe') -Arguments @('-l', '-f', $keyPath)
        Copy-UserBackupFile -Source (Join-Path $Root 'etc') -Destination $original -FileName 'sshd_config'
        $config = Join-Path $Root 'etc\sshd_config'
        $sddl = (Get-Acl -LiteralPath $config).Sddl
        [IO.File]::WriteAllText((Join-Path $backup 'sshd_config.sddl'), $sddl, (New-Object Text.UTF8Encoding($false)))
        $text = [IO.File]::ReadAllText((Join-Path $original 'sshd_config'))
        $updated = Update-UserAllowList -Text $text -Name $Name
        [IO.File]::WriteAllText((Join-Path $proposed 'sshd_config'), $updated, (New-Object Text.UTF8Encoding($false)))
        Write-Host "Configuration backup: $original"
        if ($wasRunning) {
            Stop-Service -Name $ServiceName -ErrorAction Stop
            (Get-Service -Name $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
        }
        $mutating = $true
        if ($updated -cne $text) {
            $configAttempted = $true
            Copy-UserBackupFile -Source $proposed -Destination (Join-Path $Root 'etc') -FileName 'sshd_config'
            if ((Get-Acl -LiteralPath $config).Sddl -cne $sddl) { throw 'Configuration owner or ACL changed unexpectedly.' }
        }
        $null = Invoke-UserTool -File $bash -Arguments @('--noprofile', '--norc', '-c', '/usr/sbin/sshd -t')
        $sshDir = Join-Path $userHome '.ssh'
        $null = [IO.Directory]::CreateDirectory($sshDir)
        $authorized = Join-Path $sshDir 'authorized_keys'
        [IO.File]::WriteAllText($authorized, $key, (New-Object Text.UTF8Encoding($false)))
        foreach ($path in @($authorized, $sshDir, $userHome)) {
            $null = Invoke-UserTool -File "$env:SystemRoot\System32\icacls.exe" -Arguments @($path, '/setowner', ('*' + $account.SID.Value))
        }
        $null = Invoke-UserTool -File $bash -Arguments @('--noprofile', '--norc', '/install-user.sh', 'configure', $Name, $fields[2])
        if ($wasRunning -and -not $NoRestart) { Start-Service -Name $ServiceName -ErrorAction Stop }
        Write-Host "Prepared non-administrator account: $Name; Cygwin home: /home/$Name"
        if (-not $wasRunning -or $NoRestart) { Write-Host 'The selected service remains stopped. Start it after reviewing the setup.' }
    } catch {
        $failure = $_.Exception.Message
        if ($mutating) {
            try {
                Stop-Service -Name $ServiceName -ErrorAction Stop
                (Get-Service -Name $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
            } catch { Write-Warning 'Could not confirm that the selected service is stopped. Stop it before recovery.' }
        }
        if ($configAttempted) {
            try { Copy-UserBackupFile -Source (Join-Path $backup 'original') -Destination (Join-Path $Root 'etc') -FileName 'sshd_config' }
            catch { Write-Warning "Configuration restore failed. Recover from $backup before starting the service." }
        }
        if ($mutating) { Write-Warning 'Setup failed. Leave the service stopped; review configuration and any newly created home before restarting.' }
        throw $failure
    } finally {
        $lock.Dispose()
        [IO.File]::Delete($lockPath)
    }
}

Export-ModuleMember -Function Install-OpenSshUser, Update-UserAllowList, ConvertTo-PublicKeyLine, Assert-LocalNonAdmin, Assert-UserName
