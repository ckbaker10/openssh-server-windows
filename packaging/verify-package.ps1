# Compatible with Windows PowerShell 5.1; no JSON parsing is required.
[CmdletBinding()]
param([string]$Path = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/')
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$checked = 0
$failed = 0
foreach ($line in Get-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'SHA256SUMS')) {
    if ($line -notmatch '^([0-9a-fA-F]{64})  (.+)$') { throw 'Invalid SHA256SUMS entry.' }
    $expected = $Matches[1]
    $relative = $Matches[2]
    if (-not $seen.Add($relative)) { throw 'Duplicate checksum path.' }
    $target = [System.IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $target.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Checksum path leaves the package directory.'
    }
    $checked++
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        Write-Warning "Missing file: $relative"
        $failed++
    } elseif ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $expected) {
        Write-Warning "Hash mismatch: $relative"
        $failed++
    }
}
if ($checked -eq 0) { throw 'No checksum entries were checked.' }
if ($failed -gt 0) { throw "$failed of $checked files failed verification." }
[PSCustomObject]@{ Checked = $checked; Failed = $failed; Result = 'PASS' }
