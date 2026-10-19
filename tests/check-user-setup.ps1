# Pure policy checks and orchestration with mocked Windows/native boundaries.
param([string]$ModulePath = '/project/work/zip-check/openssh-10.6p1-cygwin-x86_64/user-setup.psm1')
$ErrorActionPreference = 'Stop'
Import-Module $modulePath -Force
$checks = 0
function Check($Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:checks++
}
function Reject([scriptblock]$Action, [string]$Message) {
    $rejected = $false
    try { & $Action | Out-Null } catch { $rejected = $true }
    Check $rejected $Message
}
$nativeModule = Get-Module user-setup
Reject { & $nativeModule { Invoke-UserTool -File /bin/sh -Arguments @('-c', 'exit 8') } } 'Native exit 8 was ignored'
$nativeResult = & $nativeModule { Invoke-UserTool -File /bin/sh -Arguments @('-c', 'echo allowed; exit 7') -SuccessCodes (0..7) }
Check ($nativeResult -eq 'allowed') 'Allowed native exit 7 rejected'
Reject { & $nativeModule { Invoke-UserTool -File /missing/openssh-user-test } } 'Missing executable accepted'
foreach ($name in @('../bad', 'a b', 'name@host', 'x;exit', 'tail.', '', ('a' * 21))) {
    Reject { Assert-UserName $name } 'Unsafe name accepted'
}
$key = "ssh-ed25519 AAAA test`r`n"
Check ((ConvertTo-PublicKeyLine $key) -ceq "ssh-ed25519 AAAA test`n") 'Key LF conversion failed'
foreach ($bad in @('-----BEGIN OPENSSH PRIVATE KEY-----', 'command="x" ssh-ed25519 AAAA', "ssh-ed25519 AAAA`nssh-ed25519 AAAA", 'ssh-ed25519 not-base64')) {
    Reject { ConvertTo-PublicKeyLine $bad } 'Invalid/private/multiple keys accepted'
}
$config = "# AllowUsers old`nAllowUsers Administrator # keep`nMatch User other`n    AllowUsers onlymatch`n"
$updated = Update-UserAllowList $config sshtest
Check ($updated.Contains("AllowUsers Administrator sshtest # keep`n")) 'Global AllowUsers not extended'
Check ($updated.Contains("    AllowUsers onlymatch`n")) 'Match block changed'
Check ((Update-UserAllowList $updated sshtest) -ceq $updated) 'Duplicate AllowUsers entry'
$multiple = "AllowUsers sshtest`nAllowUsers Administrator`n"
Check ((Update-UserAllowList $multiple sshtest) -ceq $multiple) 'Existing entry in another directive duplicated'
$none = "Port 2222`nMatch User other`n  AllowUsers onlymatch`n"
Check ((Update-UserAllowList $none sshtest) -ceq $none) 'Missing global allowlist was introduced'
Reject { Update-UserAllowList "Include extra.conf`nAllowUsers Administrator`n" sshtest } 'Include not refused'
Reject { Update-UserAllowList 'AllowUsers "name with space"' sshtest } 'Quoted pattern not refused'
Check ((Update-UserAllowList "AllowUsers old#name # keep`n" sshtest) -ceq "AllowUsers old#name sshtest # keep`n") 'Hash inside an existing name was truncated'

foreach ($scenario in @('success', 'stopped', 'force-start', 'no-restart', 'conflicting-options', 'syntax-failure', 'mode-failure', 'start-failure', 'admin', 'existing-home', 'wrong-sid', 'wrong-home', 'foreign-service', 'copy-failure')) {
    $module = Import-Module $modulePath -Force -PassThru
    $root = Join-Path ([IO.Path]::GetTempPath()) ('openssh-user test-' + [guid]::NewGuid().ToString('N'))
    $null = [IO.Directory]::CreateDirectory((Join-Path $root 'etc'))
    $null = [IO.Directory]::CreateDirectory((Join-Path $root 'var/run'))
    $null = [IO.Directory]::CreateDirectory((Join-Path $root 'home'))
    $activeConfig = Join-Path $root 'etc/sshd_config'
    [IO.File]::WriteAllText($activeConfig, "AllowUsers Administrator`n")
    $pub = Join-Path $root 'test.pub'
    [IO.File]::WriteAllText($pub, "ssh-ed25519 AAAA test`n")
    if ($scenario -eq 'existing-home') { $null = [IO.Directory]::CreateDirectory((Join-Path $root 'home/sshtest')) }
    & $module {
        param($Scenario, $Root)
        $script:scenario = $Scenario
        $script:root = $Root
        $script:actions = New-Object 'Collections.Generic.List[string]'
        $script:running = $Scenario -notin @('stopped', 'force-start')
        $script:account = [pscustomobject]@{ Name = 'sshtest'; Enabled = $true; SID = [pscustomobject]@{ Value = 'S-1-5-21-1234-1001' } }
        function script:Assert-UserAdministrator { }
        function script:Get-LocalUser { return $script:account }
        function script:Get-LocalGroupMember {
            if ($script:scenario -eq 'admin') { return $script:account }
        }
        function script:Get-Acl { return [pscustomobject]@{ Sddl = 'unchanged-owner-and-acl' } }
        function script:Get-CimInstance {
            $path = '"' + (Join-Path $script:root 'bin/cygrunsrv.exe') + '"'
            if ($script:scenario -eq 'foreign-service') { $path = 'foreign-service.exe' }
            return [pscustomobject]@{ PathName = $path; StartName = 'LocalSystem'; State = $(if ($script:scenario -in @('stopped', 'force-start')) { 'Stopped' } else { 'Running' }) }
        }
        function script:Stop-Service { $script:actions.Add('stop'); $script:running = $false }
        function script:Start-Service {
            $script:actions.Add('start'); $script:running = $true
            if ($script:scenario -eq 'start-failure') { throw 'Simulated start failure after state change' }
        }
        function script:Get-Service { return New-Object PSObject | Add-Member -MemberType ScriptMethod -Name WaitForStatus -Value { } -PassThru }
        function script:Invoke-UserTool {
            param($File, $Arguments, $SuccessCodes)
            if ($File -like '*robocopy.exe') {
                if ($Arguments -notcontains '/B' -or $Arguments -notcontains '/COPY:DAT' -or $Arguments -notcontains '/IS' -or $Arguments -notcontains '/IT') { throw 'Unsafe copy arguments' }
                if ($script:scenario -eq 'copy-failure') { throw 'Simulated backup copy failure' }
                $null = [IO.Directory]::CreateDirectory($Arguments[1])
                [IO.File]::Copy((Join-Path $Arguments[0] $Arguments[2]), (Join-Path $Arguments[1] $Arguments[2]), $true)
                $script:actions.Add('copy')
            } elseif ($File -like '*bash.exe') {
                if ($Arguments -contains 'inspect') {
                    $sid = $script:account.SID.Value
                    $userHome = '/home/sshtest'
                    if ($script:scenario -eq 'wrong-sid') { $sid = 'S-1-5-21-9999-1001' }
                    if ($script:scenario -eq 'wrong-home') { $userHome = '/cygdrive/c/Users/sshtest' }
                    return 'sshtest:*:197609:197121:U-TEST+sshtest,' + $sid + ':' + $userHome + ':/bin/bash'
                }
                if ($Arguments -contains '-c') {
                    if ($Arguments[-1] -cne 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t') { throw 'Missing explicit Cygwin PATH (simulated exit 127)' }
                    $script:actions.Add('syntax')
                    if ($script:scenario -eq 'syntax-failure') { throw 'Simulated syntax failure' }
                }
                if ($Arguments -contains 'configure') {
                    $script:actions.Add('modes')
                    if ($script:scenario -eq 'mode-failure') { throw 'Simulated chmod failure' }
                }
            } elseif ($File -like '*icacls.exe' -and $Arguments -contains '/setowner') {
                if ($Arguments[-1] -ne ('*' + $script:account.SID.Value)) { throw 'Wrong owner SID' }
                $script:actions.Add('owner')
            }
        }
    } $scenario $root
    try {
        $failed = $false
        try { Install-OpenSshUser -Root $root -Name sshtest -PublicKeyFile $pub -NoRestart:($scenario -in @('no-restart', 'conflicting-options')) -Start:($scenario -in @('force-start', 'conflicting-options')) } catch { $failed = $true }
        $actions = @(& $module { $script:actions.ToArray() })
        if ($scenario -in @('success', 'stopped', 'force-start', 'no-restart')) {
            Check (-not $failed) "$scenario failed"
            Check ([IO.File]::ReadAllText($activeConfig).Contains('Administrator sshtest')) 'AllowUsers not written'
            Check ([IO.File]::ReadAllText((Join-Path $root 'home/sshtest/.ssh/authorized_keys')) -ceq "ssh-ed25519 AAAA test`n") 'Key content differs'
            Check (@($actions | Where-Object { $_ -eq 'owner' }).Count -eq 3) 'Ownership was not limited to 3 paths'
            Check (($actions -contains 'start') -eq ($scenario -in @('success', 'force-start'))) 'Incorrect start behavior'
            Check (($actions -contains 'stop') -eq ($scenario -notin @('stopped', 'force-start'))) 'Incorrect stop behavior'
        } else {
            Check $failed "Expected refusal for $scenario"
            if ($scenario -eq 'start-failure') {
                Check (-not (& $module { $script:running })) 'Failed start was not stopped again'
            } else { Check ($actions -notcontains 'start') 'Service started after failure' }
            Check ([IO.File]::ReadAllText($activeConfig) -ceq "AllowUsers Administrator`n") 'Config not restored/preserved'
            if ($scenario -notin @('syntax-failure', 'mode-failure', 'start-failure')) { Check ($actions -notcontains 'stop') 'Service stopped during preflight refusal' }
        }
        Check (-not [IO.File]::Exists((Join-Path $root 'var/run/install-user.lock'))) 'Lock not released'
        Write-Output "$scenario : PASS"
    } finally {
        Remove-Item -LiteralPath $root -Recurse -Force
    }
}
foreach ($file in Get-ChildItem -LiteralPath (Split-Path -Parent $ModulePath) -File | Where-Object { $_.Extension -in @('.ps1', '.psm1') }) {
    $tokens = $null; $parseErrors = $null
    $null = [Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors)
    Check ($parseErrors.Count -eq 0) ('Parse error: ' + $file.Name)
}
Write-Output "$checks checks: PASS (PowerShell $($PSVersionTable.PSVersion), mocked Windows boundaries)"
