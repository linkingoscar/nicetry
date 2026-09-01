[CmdletBinding()]
param(
    [ValidateSet('Quick', 'Targeted', 'Statistical', 'Full', 'Release')]
    [string]$Mode = 'Quick',
    [ValidateRange(1, 16)]
    [int]$PytestWorkers = 4,
    [string]$BaseRef = 'HEAD~1',
    [string[]]$ChangedFile = @(),
    [switch]$SkipDependencyAudit,
    [switch]$SkipBenchmark
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$ruff = Join-Path $root '.venv\Scripts\ruff.exe'
$releaseEvidence = Join-Path $root 'output\release\local-evidence.json'

function Assert-LastExitCode {
    param([Parameter(Mandatory)][string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Invoke-QuickHarness {
    & (Join-Path $PSScriptRoot 'check-architecture.ps1')

    & $ruff check apps/api/app apps/api/tests
    Assert-LastExitCode 'Python lint'

    & $python (Join-Path $PSScriptRoot 'check-python-types.py')
    Assert-LastExitCode 'Python type baseline'

    & npm run lint:web
    Assert-LastExitCode 'Web lint'

    & npm run typecheck:web
    Assert-LastExitCode 'Web typecheck'

    & (Join-Path $PSScriptRoot 'generate-contracts.ps1') -Check
}

function Write-ReleaseEvidence {
    param(
        [Parameter(Mandatory)][ValidateSet('passed', 'failed', 'incomplete')][string]$Status,
        [string[]]$RequiredStep = @(),
        [string[]]$CompletedStep = @(),
        [string[]]$SkippedStep = @(),
        [double]$DurationSeconds = 0
    )
    if (-not (Test-Path -LiteralPath $python)) {
        Write-Warning 'Python runtime is unavailable; release evidence was not written.'
        return
    }
    $arguments = @(
        (Join-Path $PSScriptRoot 'release-evidence.py'),
        '--test-status', $Status,
        '--mode', $Mode,
        '--duration-seconds', $DurationSeconds,
        '--output', $releaseEvidence
    )
    if ($env:GITHUB_RUN_ID) { $arguments += @('--run-id', $env:GITHUB_RUN_ID) }
    foreach ($step in $RequiredStep) { $arguments += @('--required-step', $step) }
    foreach ($step in $CompletedStep) { $arguments += @('--completed-step', $step) }
    foreach ($step in $SkippedStep) { $arguments += @('--skipped-step', $step) }
    & $python @arguments
    Assert-LastExitCode 'Release evidence generation'
}

Push-Location $root
try {
    $harnessStatus = 'passed'
    Write-Host "ResearchPath harness: $Mode" -ForegroundColor Cyan
    switch ($Mode) {
        'Quick' {
            Invoke-QuickHarness
        }
        'Targeted' {
            Invoke-QuickHarness
            $impactArguments = @(
                (Join-Path $PSScriptRoot 'resolve-test-impact.py'),
                '--root', $root,
                '--base-ref', $BaseRef
            )
            foreach ($path in $ChangedFile) {
                $impactArguments += @('--changed-file', $path)
            }
            $impactJson = & $python @impactArguments
            Assert-LastExitCode 'Test impact resolution'
            $impact = $impactJson | ConvertFrom-Json
            Write-Host ($impact | ConvertTo-Json -Depth 5) -ForegroundColor DarkCyan
            if ($impact.escalation -eq 'Full') {
                Write-Warning 'Targeted impact is broad or unknown; escalating to Full.'
                & (Join-Path $PSScriptRoot 'test.ps1') `
                    -PytestWorkers $PytestWorkers `
                    -HarnessMode Full
            }
            elseif ($impact.escalation) {
                throw "Unsupported targeted escalation: $($impact.escalation)"
            }
            else {
                & (Join-Path $PSScriptRoot 'run-targeted-tests.ps1') `
                    -Lane @($impact.lanes) `
                    -PytestWorkers $PytestWorkers
            }
        }
        'Statistical' {
            Invoke-QuickHarness
            & (Join-Path $PSScriptRoot 'run-targeted-tests.ps1') `
                -Lane @('api-no-coverage', 'contracts', 'r-goldens', 'r-statistical', 'web-unit') `
                -PytestWorkers $PytestWorkers
        }
        'Full' {
            & (Join-Path $PSScriptRoot 'test.ps1') `
                -PytestWorkers $PytestWorkers `
                -HarnessMode Full
        }
        'Release' {
            $releaseTimer = [System.Diagnostics.Stopwatch]::StartNew()
            $releaseStatus = 'passed'
            $requiredSteps = @(
                'quality-gate',
                'dependency-audit',
                'r-runtime-benchmark'
            )
            $completedSteps = @()
            $skippedSteps = @()
            try {
                & (Join-Path $PSScriptRoot 'test.ps1') `
                    -PytestWorkers $PytestWorkers `
                    -NoLockCache `
                    -NoNumericBaselineCache `
                    -HarnessMode Release
                $completedSteps += 'quality-gate'
                if (-not $SkipDependencyAudit) {
                    & (Join-Path $PSScriptRoot 'audit-dependencies.ps1')
                    $completedSteps += 'dependency-audit'
                } else {
                    $releaseStatus = 'incomplete'
                    $skippedSteps += 'dependency-audit'
                }
                if (-not $SkipBenchmark) {
                    & $python (Join-Path $PSScriptRoot 'benchmark-r-runtime.py')
                    Assert-LastExitCode 'R runtime benchmark'
                    $completedSteps += 'r-runtime-benchmark'
                } else {
                    $releaseStatus = 'incomplete'
                    $skippedSteps += 'r-runtime-benchmark'
                }
                $releaseTimer.Stop()
                Write-ReleaseEvidence `
                    -Status $releaseStatus `
                    -RequiredStep $requiredSteps `
                    -CompletedStep $completedSteps `
                    -SkippedStep $skippedSteps `
                    -DurationSeconds $releaseTimer.Elapsed.TotalSeconds
            }
            catch {
                $releaseTimer.Stop()
                try {
                    Write-ReleaseEvidence `
                        -Status failed `
                        -RequiredStep $requiredSteps `
                        -CompletedStep $completedSteps `
                        -SkippedStep $skippedSteps `
                        -DurationSeconds $releaseTimer.Elapsed.TotalSeconds
                }
                catch {
                    Write-Warning "Failed to write failure evidence: $($_.Exception.Message)"
                }
                throw
            }
            if ($releaseStatus -eq 'incomplete') {
                $harnessStatus = 'incomplete'
            }
        }
    }
    if ($harnessStatus -eq 'incomplete') {
        Write-Warning "ResearchPath harness incomplete: $Mode (release steps were skipped)"
        exit 2
    }
    Write-Host "ResearchPath harness passed: $Mode" -ForegroundColor Green
}
finally {
    Pop-Location
}
