# Run from an elevated 64-bit Windows PowerShell terminal.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Name,
    [Parameter(Mandatory = $true, Position = 1)][string]$PublicKeyFile,
    [string]$ServiceName = 'openssh-cygwin',
    [switch]$NoRestart
)
$ErrorActionPreference = 'Stop'
try {
    $root = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($root)) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }
    Import-Module (Join-Path $root 'user-setup.psm1') -Force
    Install-OpenSshUser -Root $root -Name $Name -PublicKeyFile $PublicKeyFile -ServiceName $ServiceName -NoRestart:$NoRestart
} catch {
    Write-Error -ErrorAction Continue $_.Exception.Message
    exit 1
}
