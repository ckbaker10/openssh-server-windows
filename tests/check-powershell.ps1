# Execute in the Linux PowerShell test container after check-package.py.
$ErrorActionPreference = 'Stop'
$package = '/project/work/zip-check/openssh-10.6p1-cygwin-x86_64'
$verify = Join-Path $package 'verify-package.ps1'
Push-Location ([IO.Path]::GetTempPath())
try { & $verify } finally { Pop-Location }
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("& '$verify' | Out-Null"))
& pwsh -NoProfile -NonInteractive -EncodedCommand $encoded
if ($LASTEXITCODE -ne 0) { throw 'Default path failed in a noninteractive encoded invocation.' }
Write-Output 'Noninteractive default path from another directory: PASS'
if ($PSVersionTable.PSVersion.Major -ne 7) { throw 'Record the changed PowerShell test environment.' }
Write-Output ('PowerShell runtime: ' + $PSVersionTable.PSVersion)
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('openssh-check-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $fixture | Out-Null
try {
    $file = Join-Path $fixture 'payload'
    $sums = Join-Path $fixture 'SHA256SUMS'
    [IO.File]::WriteAllText($file, 'original')
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
    $entry = $hash + '  payload' + "`n"
    [IO.File]::WriteAllText($sums, $entry)
    & $verify -Path $fixture
    $fallback = Join-Path $fixture 'verify-fallback.ps1'
    $code = [IO.File]::ReadAllText($verify).Replace('$Path = $PSScriptRoot', '$Path = [string]::Empty')
    [IO.File]::WriteAllText($fallback, $code)
    & $fallback
    Write-Output 'Empty ScriptRoot with MyInvocation fallback: PASS'
    foreach ($case in 'tampered', 'empty', 'duplicate', 'escape', 'missing') {
        [IO.File]::WriteAllText($file, 'original')
        [IO.File]::WriteAllText($sums, $entry)
        switch ($case) {
            'tampered' { [IO.File]::WriteAllText($file, 'modified') }
            'empty' { [IO.File]::WriteAllText($sums, '') }
            'duplicate' { [IO.File]::WriteAllText($sums, $entry + $entry) }
            'escape' { [IO.File]::WriteAllText($sums, $hash + '  ../outside' + "`n") }
            'missing' { Remove-Item -LiteralPath $file }
        }
        $rejected = $false
        try { & $verify -Path $fixture | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw "Failed to reject $case" }
        Write-Output ("Rejected $case : PASS")
    }
} finally {
    Remove-Item -LiteralPath $fixture -Recurse
}
