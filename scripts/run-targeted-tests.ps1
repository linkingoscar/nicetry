[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Lane,
    [ValidateRange(1, 16)][int]$PytestWorkers = 4
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$knownLanes = @(
    'api-no-coverage',
    'contracts',
    'docs-only',
    'e2e-smoke',
    'r-goldens',
    'r-statistical',
    'web-unit'
)
$selected = @($Lane | Sort-Object -Unique)
$unknown = @($selected | Where-Object { $_ -notin $knownLanes })
if ($unknown.Count -gt 0) {
    throw "Unknown targeted test lane(s): $($unknown -join ', ')"
}

function Assert-LastExitCode {
    param([Parameter(Mandatory)][string]$Step)
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE." }
}

Push-Location $root
try {
    Write-Host "Targeted lanes: $($selected -join ', ')" -ForegroundColor Cyan

    if ('contracts' -in $selected) {
        & (Join-Path $PSScriptRoot 'generate-contracts.ps1') -Check
        Assert-LastExitCode 'Contract generation check'
    }

    if ('api-no-coverage' -in $selected) {
        Push-Location (Join-Path $root 'apps\api')
        $previousLocale = $env:LC_ALL
        try {
            $env:LC_ALL = 'English_United States.utf8'
            & $python -m pytest -m 'not serial' -n $PytestWorkers --dist=worksteal --max-worker-restart=0
            Assert-LastExitCode 'Targeted parallel API tests'
            & $python -m pytest -m serial -n 0
            Assert-LastExitCode 'Targeted serial API tests'
        }
        finally {
            $env:LC_ALL = $previousLocale
            Pop-Location
        }
    }

    if (('r-statistical' -in $selected) -or ('r-goldens' -in $selected)) {
        $previousRLibrary = $env:R_LIBS_USER
        $previousLocale = $env:LC_ALL
        try {
            $env:R_LIBS_USER = Join-Path $root '.runtime\R-library'
            $env:LC_ALL = 'English_United States.utf8'
            & (Join-Path $root '.runtime\R\bin\Rscript.exe') --vanilla (Join-Path $PSScriptRoot 'check-r-lock.R') $root
            Assert-LastExitCode 'R lock verification'
            if ('r-goldens' -in $selected) {
                & $python (Join-Path $PSScriptRoot 'check-r-numeric-baselines.py')
                Assert-LastExitCode 'R numeric baseline verification'
            }
            & (Join-Path $PSScriptRoot 'test-r.ps1')
            Assert-LastExitCode 'R statistical tests'
        }
        finally {
            $env:R_LIBS_USER = $previousRLibrary
            $env:LC_ALL = $previousLocale
        }
    }

    if ('web-unit' -in $selected) {
        & npm run test:web
        Assert-LastExitCode 'Web tests'
    }

    if ('e2e-smoke' -in $selected) {
        $apiListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $apiListener.Start()
        $e2eApiPort = $apiListener.LocalEndpoint.Port
        $apiListener.Stop()
        $webListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $webListener.Start()
        $e2eWebPort = $webListener.LocalEndpoint.Port
        $webListener.Stop()

        $previousApiPort = $env:RESEARCHPATH_E2E_API_PORT
        $previousWebPort = $env:RESEARCHPATH_E2E_WEB_PORT
        try {
            $env:RESEARCHPATH_E2E_API_PORT = [string]$e2eApiPort
            $env:RESEARCHPATH_E2E_WEB_PORT = [string]$e2eWebPort
            & npm run test:e2e -- --grep '@smoke'
            Assert-LastExitCode 'Browser smoke tests'
        }
        finally {
            $env:RESEARCHPATH_E2E_API_PORT = $previousApiPort
            $env:RESEARCHPATH_E2E_WEB_PORT = $previousWebPort
        }
    }
}
finally {
    Pop-Location
}

Write-Host 'Targeted test lanes passed.' -ForegroundColor Green
