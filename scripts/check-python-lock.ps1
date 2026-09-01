[CmdletBinding()]
param(
    [switch]$Update,
    [switch]$NoCache
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$inputRelative = 'apps/api/requirements.in'
$lockRelative = 'apps/api/requirements.lock'
$lockPath = Join-Path $root $lockRelative
$cachePath = Join-Path $root '.pytest-tmp/python-lock-verification.json'
$cacheVersion = 1

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python virtual environment is missing. Run scripts/setup.ps1 first.'
}

$inputHash = (Get-FileHash -LiteralPath (Join-Path $root $inputRelative) -Algorithm SHA256).Hash
$lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
$pythonIdentity = (& $python -c "import importlib.metadata, platform; print(f'{platform.python_version()}|{importlib.metadata.version(""pip-tools"")}')").Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to determine the Python/pip-tools identity.'
}

if (-not $Update -and -not $NoCache -and (Test-Path -LiteralPath $cachePath)) {
    try {
        $cached = Get-Content -LiteralPath $cachePath -Encoding UTF8 -Raw | ConvertFrom-Json
        if (
            $cached.cacheVersion -eq $cacheVersion -and
            $cached.inputHash -eq $inputHash -and
            $cached.lockHash -eq $lockHash -and
            $cached.pythonIdentity -eq $pythonIdentity
        ) {
            Write-Host 'Python dependency lock is reproducible and current (verified cache).' -ForegroundColor Green
            exit 0
        }
    }
    catch {
        Write-Verbose "Ignoring invalid Python lock verification cache: $($_.Exception.Message)"
    }
}

$targetRelative = if ($Update) {
    $lockRelative
} else {
    ".pytest-tmp/python-lock-$([guid]::NewGuid().ToString('N')).lock"
}
$target = Join-Path $root $targetRelative

Push-Location $root
try {
    if (-not $Update) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $lockPath -Destination $target
    }
    $compileArguments = @(
        '-m', 'piptools', 'compile',
        '--allow-unsafe',
        '--generate-hashes',
        '--no-header',
        '--quiet',
        '--resolver=backtracking',
        '--no-strip-extras',
        '--output-file', $targetRelative
    )
    if ($Update) { $compileArguments += '--upgrade' }
    $compileArguments += $inputRelative
    & $python @compileArguments
    if ($LASTEXITCODE -ne 0) { throw 'Python lock compilation failed.' }

    if (-not $Update) {
        $expected = (Get-Content -LiteralPath $lockPath -Raw).Replace("`r`n", "`n")
        $actual = (Get-Content -LiteralPath $target -Raw).Replace("`r`n", "`n")
        if ($expected -ne $actual) {
            throw 'Python dependency lock is stale. Run scripts/check-python-lock.ps1 -Update.'
        }
    }
}
finally {
    if (-not $Update -and (Test-Path -LiteralPath $target)) {
        Remove-Item -LiteralPath $target -Force
    }
    Pop-Location
}

if ($Update) {
    Remove-Item -LiteralPath $cachePath -Force -ErrorAction SilentlyContinue
    Write-Host 'Python dependency lock updated with hashes.' -ForegroundColor Green
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $cachePath) | Out-Null
    [ordered]@{
        cacheVersion = $cacheVersion
        inputHash = $inputHash
        lockHash = $lockHash
        pythonIdentity = $pythonIdentity
        verifiedAt = [DateTimeOffset]::UtcNow.ToString('O')
    } | ConvertTo-Json | Set-Content -LiteralPath $cachePath -Encoding UTF8
    Write-Host 'Python dependency lock is reproducible and current.' -ForegroundColor Green
}
