# Execute in the Linux PowerShell test container after check-package.py.
$ErrorActionPreference = 'Stop'
$package = '/project/work/zip-check/openssh-10.6p1-cygwin-x86_64'
$verify = Join-Path $package 'verify-package.ps1'
& $verify
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
