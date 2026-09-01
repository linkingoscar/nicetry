[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$lockPath = Join-Path $root 'apps\api\requirements.lock'

Push-Location $root
try {
    & $python -m pip_audit --disable-pip -r $lockPath
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency vulnerability audit failed.' }
    & npm audit --audit-level=high
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency vulnerability audit failed.' }
}
finally {
    Pop-Location
}

Write-Host 'Dependency vulnerability audits passed.' -ForegroundColor Green
