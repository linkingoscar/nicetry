[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$openApiTarget = Join-Path $root 'specs\openapi.json'
$typeTarget = Join-Path $root 'apps\web\src\types\generated-api.ts'

$processArguments = @((Join-Path $PSScriptRoot 'generate-process-templates.py'))
if ($Check) { $processArguments += '--check' }
& $python @processArguments
if ($LASTEXITCODE -ne 0) { throw 'PROCESS preset generation check failed.' }

function Invoke-Generation([string]$openApiPath, [string]$typePath) {
    & $python (Join-Path $PSScriptRoot 'export_openapi.py') --output $openApiPath
    if ($LASTEXITCODE -ne 0) { throw 'OpenAPI export failed.' }
    Push-Location $root
    try {
        & npx openapi-typescript $openApiPath --output $typePath
        if ($LASTEXITCODE -ne 0) { throw 'TypeScript contract generation failed.' }
    }
    finally {
        Pop-Location
    }
}

if (-not $Check) {
    Invoke-Generation $openApiTarget $typeTarget
    Write-Host 'OpenAPI and TypeScript contracts generated.' -ForegroundColor Green
    exit 0
}

$temporaryOpenApi = [IO.Path]::GetTempFileName()
$temporaryTypes = [IO.Path]::GetTempFileName()
try {
    Invoke-Generation $temporaryOpenApi $temporaryTypes
    foreach ($pair in @(
        @($temporaryOpenApi, $openApiTarget),
        @($temporaryTypes, $typeTarget)
    )) {
        if (-not (Test-Path -LiteralPath $pair[1])) {
            throw "Generated contract is missing: $($pair[1])"
        }
        $generatedHash = (Get-FileHash -LiteralPath $pair[0] -Algorithm SHA256).Hash
        $committedHash = (Get-FileHash -LiteralPath $pair[1] -Algorithm SHA256).Hash
        if ($generatedHash -ne $committedHash) {
            throw "Generated contracts are stale. Run scripts/generate-contracts.ps1."
        }
    }
    & $python (Join-Path $PSScriptRoot 'check_contract_consistency.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'JSON Schema <-> Pydantic <-> OpenAPI representative parity failed.'
    }
}
finally {
    Remove-Item -LiteralPath $temporaryOpenApi, $temporaryTypes -Force -ErrorAction SilentlyContinue
}

Write-Host 'Generated contracts are current.' -ForegroundColor Green
