[CmdletBinding()]
param(
    [string]$Capability,
    [string]$Scenario,
    [switch]$Regenerate,
    [switch]$All,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

Write-Host "=== ResearchPath Golden Standards Infrastructure CLI ===" -ForegroundColor Cyan

# Step 1: Check reference independence
Write-Host "[1/4] Checking reference implementation independence..." -ForegroundColor Yellow
& $python (Join-Path $PSScriptRoot 'check-reference-independence.py')
if ($LASTEXITCODE -ne 0) {
    throw "Reference independence check failed."
}

# Step 2: Verification Mode
if ($VerifyOnly -or (-not $Regenerate)) {
    Write-Host "[2/4] Executing SUT outputs population..." -ForegroundColor Yellow
    & $python (Join-Path $root 'tools\goldens\sut_runner.py') --all
    if ($LASTEXITCODE -ne 0) {
        throw "SUT runner execution failed."
    }

    Write-Host "[3/4] Verifying Golden Cases against tolerances..." -ForegroundColor Yellow
    & $python (Join-Path $root 'tools\goldens\verify.py') --all --require-sut
    if ($LASTEXITCODE -ne 0) {
        throw "Golden cases verification failed."
    }

    Write-Host "[4/4] Running dynamic metamorphic invariants..." -ForegroundColor Yellow
    & $python (Join-Path $root 'tools\goldens\invariants.py') --all
    if ($LASTEXITCODE -ne 0) {
        throw "Metamorphic invariant tests failed."
    }

    Write-Host "✨ All Golden Standard verifications passed cleanly!" -ForegroundColor Green
    exit 0
}

# Step 3: Explicit Regenerate Mode
Write-Host "[REGENERATE] Regenerating hashes and freezing Golden Cases..." -ForegroundColor Red
if ($Capability) {
    Write-Host "Target Capability: $Capability" -ForegroundColor Yellow
}
if ($Scenario) {
    Write-Host "Target Scenario: $Scenario" -ForegroundColor Yellow
}

Write-Host "Running golden freeze tool..." -ForegroundColor Yellow
& $python (Join-Path $root 'tools\goldens\freeze.py')
if ($LASTEXITCODE -ne 0) {
    throw "Golden freeze failed."
}

Write-Host "Running SUT runner..." -ForegroundColor Yellow
& $python (Join-Path $root 'tools\goldens\sut_runner.py') --all

Write-Host "Re-verifying regenerated cases..." -ForegroundColor Yellow
& $python (Join-Path $root 'tools\goldens\verify.py') --all --require-sut

Write-Host "✨ Golden standard regeneration and hash freezing completed successfully!" -ForegroundColor Green
