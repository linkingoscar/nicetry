[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$ExitAfterReady
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$apiDirectory = Join-Path $root 'apps\api'
$stateDirectory = Join-Path $root '.researchpath\logs'
$apiPort = 9999
$webPort = 5173

function Get-ProcessSnapshot {
    @(Get-CimInstance Win32_Process)
}

function Get-DescendantProcessIds {
    param(
        [Parameter(Mandatory)][int]$RootProcessId,
        [Parameter(Mandatory)][object[]]$Snapshot
    )

    $descendants = [System.Collections.Generic.List[int]]::new()
    $pending = [System.Collections.Generic.Queue[int]]::new()
    $pending.Enqueue($RootProcessId)
    while ($pending.Count -gt 0) {
        $parentId = $pending.Dequeue()
        foreach ($child in $Snapshot | Where-Object { $_.ParentProcessId -eq $parentId }) {
            $childId = [int]$child.ProcessId
            if (-not $descendants.Contains($childId)) {
                $descendants.Add($childId)
                $pending.Enqueue($childId)
            }
        }
    }
    return $descendants.ToArray()
}

function Test-IsResearchPathDevProcess {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][int]$ProcessId,
        [Parameter(Mandatory)][object[]]$Snapshot
    )

    $treeIds = @($ProcessId) + @(Get-DescendantProcessIds -RootProcessId $ProcessId -Snapshot $Snapshot)
    $tree = $Snapshot | Where-Object { $_.ProcessId -in $treeIds }
    $owner = $tree | Where-Object { $_.ProcessId -eq $ProcessId } | Select-Object -First 1
    $escapedRoot = [Regex]::Escape($root)
    $belongsToRoot = $tree | Where-Object {
        ($_.CommandLine -and $_.CommandLine -match $escapedRoot) -or
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase))
    }
    if (-not $belongsToRoot) { return $false }

    if ($Port -eq $apiPort) {
        if ($owner) {
            return [bool](
                $owner.CommandLine -match 'uvicorn\s+app\.main:app' -and
                $owner.CommandLine -match '--port\s+9999'
            )
        }
        # A terminated uvicorn --reload parent can leave its socket attributed
        # to the dead parent PID while a project multiprocessing child remains.
        return [bool]($tree | Where-Object {
            $_.CommandLine -match 'multiprocessing\.spawn' -and
            (
                ($_.CommandLine -and $_.CommandLine -match $escapedRoot) -or
                ($_.ExecutablePath -and $_.ExecutablePath.StartsWith(
                    $root,
                    [StringComparison]::OrdinalIgnoreCase
                ))
            )
        })
    }
    if ($Port -eq $webPort) {
        return [bool](
            $owner -and
            $owner.CommandLine -match 'vite(\.js)?' -and
            $owner.CommandLine -match '(--port\s+5173|vite\.js)'
        )
    }
    return $false
}

function Stop-ResearchPathProcessTree {
    param([Parameter(Mandatory)][int]$RootProcessId)

    $snapshot = Get-ProcessSnapshot
    $descendants = @(Get-DescendantProcessIds -RootProcessId $RootProcessId -Snapshot $snapshot)
    Stop-Process -Id $RootProcessId -Force -ErrorAction SilentlyContinue
    if ($descendants.Count -gt 0) {
        Stop-Process -Id $descendants -Force -ErrorAction SilentlyContinue
    }
}

function Clear-ResearchPathDevPort {
    param([Parameter(Mandatory)][int]$Port)

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(12)
    do {
        $connections = @(
            Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
        )
        if ($connections.Count -eq 0) { return }

        $snapshot = Get-ProcessSnapshot
        foreach ($processId in @($connections.OwningProcess | Sort-Object -Unique)) {
            if (-not (Test-IsResearchPathDevProcess -Port $Port -ProcessId $processId -Snapshot $snapshot)) {
                $process = $snapshot |
                    Where-Object { $_.ProcessId -eq $processId } |
                    Select-Object -First 1
                $description = if ($process) {
                    "$($process.Name) (PID $processId)"
                } else {
                    "PID $processId"
                }
                throw "端口 ${Port} 已被非本项目进程 $description 占用；为避免误停其他程序，研径没有继续启动。"
            }
            Write-Host "正在关闭上一轮研径进程：端口 $Port，PID $processId" -ForegroundColor DarkYellow
            Stop-ResearchPathProcessTree -RootProcessId $processId
        }
        Start-Sleep -Milliseconds 200
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    throw "上一轮研径进程未能释放端口 ${Port}。请关闭旧的「启动研径」窗口后重试。"
}

function Wait-LocalEndpoint {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][System.Diagnostics.Process[]]$Processes,
        [Parameter(Mandatory)][string[]]$ErrorLogs
    )

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(45)
    do {
        foreach ($process in $Processes) {
            $process.Refresh()
            if ($process.HasExited) {
                $details = foreach ($log in $ErrorLogs) {
                    if (Test-Path -LiteralPath $log) {
                        Get-Content -LiteralPath $log -Encoding UTF8 -Tail 20
                    }
                }
                throw "$Name 启动进程提前退出。`n$($details -join "`n")"
            }
        }
        try {
            $response = Invoke-WebRequest -Uri $Uri -Method Get -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    throw "$Name 在 45 秒内未就绪，请查看 .researchpath\logs。"
}

function Stop-TrackedProcess {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) { return }
    $Process.Refresh()
    if (-not $Process.HasExited) {
        Stop-ResearchPathProcessTree -RootProcessId $Process.Id
    }
}

New-Item -ItemType Directory -Force -Path $stateDirectory | Out-Null
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python environment is missing. Run scripts\setup.ps1 first.'
}
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

Clear-ResearchPathDevPort -Port $apiPort
Clear-ResearchPathDevPort -Port $webPort

$bootstrapBytes = [byte[]]::new(32)
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bootstrapBytes)
$bootstrapToken = ([Convert]::ToBase64String($bootstrapBytes)).
    TrimEnd('=').
    Replace('+', '-').
    Replace('/', '_')
$env:RESEARCHPATH_BOOTSTRAP_TOKEN = $bootstrapToken

$apiOutputLog = Join-Path $stateDirectory 'api.out.log'
$apiErrorLog = Join-Path $stateDirectory 'api.err.log'
$webOutputLog = Join-Path $stateDirectory 'web.out.log'
$webErrorLog = Join-Path $stateDirectory 'web.err.log'
$apiProcess = $null
$webProcess = $null

try {
    $apiProcess = Start-Process -FilePath $python -ArgumentList @(
        '-m', 'uvicorn', 'app.main:app',
        '--host', '127.0.0.1',
        '--port', [string]$apiPort
    ) -WorkingDirectory $apiDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $apiOutputLog `
        -RedirectStandardError $apiErrorLog `
        -PassThru

    Remove-Item Env:RESEARCHPATH_BOOTSTRAP_TOKEN -ErrorAction SilentlyContinue

    $webProcess = Start-Process -FilePath $npm -ArgumentList @(
        'run', 'dev:web'
    ) -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $webOutputLog `
        -RedirectStandardError $webErrorLog `
        -PassThru

    Wait-LocalEndpoint `
        -Name '本地 API' `
        -Uri "http://127.0.0.1:$apiPort/api/v1/health" `
        -Processes @($apiProcess) `
        -ErrorLogs @($apiErrorLog)
    Wait-LocalEndpoint `
        -Name '研径界面' `
        -Uri "http://127.0.0.1:$webPort/" `
        -Processes @($apiProcess, $webProcess) `
        -ErrorLogs @($apiErrorLog, $webErrorLog)

    $launchUrl = "http://localhost:$webPort/#bootstrap=$bootstrapToken"
    if (-not $NoBrowser) {
        Start-Process $launchUrl
    } else {
        Write-Output "研径地址：$launchUrl"
    }
    Write-Host '研径已经就绪，可正常导入演示项目或上传问卷。' -ForegroundColor Green
    Write-Host '使用结束后关闭本窗口，或按 Ctrl+C 停止本地服务。' -ForegroundColor Cyan

    if ($ExitAfterReady) { return }
    while ($true) {
        $apiProcess.Refresh()
        $webProcess.Refresh()
        if ($apiProcess.HasExited) {
            throw '本地 API 意外退出，请查看 .researchpath\logs\api.err.log。'
        }
        if ($webProcess.HasExited) {
            throw '研径界面服务意外退出，请查看 .researchpath\logs\web.err.log。'
        }
        Start-Sleep -Seconds 1
    }
}
finally {
    Remove-Item Env:RESEARCHPATH_BOOTSTRAP_TOKEN -ErrorAction SilentlyContinue
    Stop-TrackedProcess -Process $webProcess
    Stop-TrackedProcess -Process $apiProcess
}
