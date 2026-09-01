[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$apiDirectory = Join-Path $root 'apps\api'
$webIndex = Join-Path $root 'apps\web\dist\index.html'
$stateDirectory = Join-Path $root '.researchpath\logs'
$edgeProfile = Join-Path $root '.researchpath\edge-profile'
$apiPort = 9999
$appName = '研径 ResearchPath'
$mutex = $null
$apiProcess = $null
$launcherExitCode = 0

function Write-AppLog {
    param([Parameter(Mandatory)][string]$Message)

    New-Item -ItemType Directory -Force -Path $stateDirectory | Out-Null
    $line = '{0:yyyy-MM-dd HH:mm:ss.fff} {1}' -f [DateTime]::Now, $Message
    Add-Content -LiteralPath (Join-Path $stateDirectory 'desktop-launcher.log') `
        -Value $line -Encoding UTF8
}

function Show-AppMessage {
    param(
        [Parameter(Mandatory)][string]$Message,
        [string]$Title = $appName,
        [ValidateSet('Information', 'Warning', 'Error')][string]$Kind = 'Information'
    )

    Add-Type -AssemblyName PresentationFramework
    $icon = [System.Windows.MessageBoxImage]::$Kind
    [System.Windows.MessageBox]::Show(
        $Message,
        $Title,
        [System.Windows.MessageBoxButton]::OK,
        $icon
    ) | Out-Null
}

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

function Stop-ProjectProcessTree {
    param([Parameter(Mandatory)][int]$RootProcessId)

    $snapshot = Get-ProcessSnapshot
    $descendants = @(Get-DescendantProcessIds -RootProcessId $RootProcessId -Snapshot $snapshot)
    if ($descendants.Count -gt 0) {
        Stop-Process -Id $descendants -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $RootProcessId -Force -ErrorAction SilentlyContinue
}

function Clear-OwnedApiPort {
    $connections = @(
        Get-NetTCPConnection -State Listen -LocalPort $apiPort -ErrorAction SilentlyContinue
    )
    if ($connections.Count -eq 0) { return }

    $snapshot = Get-ProcessSnapshot
    $escapedRoot = [Regex]::Escape($root)
    foreach ($processId in @($connections.OwningProcess | Sort-Object -Unique)) {
        $process = $snapshot |
            Where-Object { $_.ProcessId -eq $processId } |
            Select-Object -First 1
        $isOwned = $process -and
            $process.CommandLine -match $escapedRoot -and
            $process.CommandLine -match 'uvicorn\s+app\.main:app' -and
            $process.CommandLine -match '--port\s+9999'
        if (-not $isOwned) {
            $description = if ($process) {
                "$($process.Name) (PID $processId)"
            } else {
                "PID $processId"
            }
            throw "端口 $apiPort 已被非本项目进程 $description 占用。研径不会关闭其他程序。"
        }
        Write-AppLog "Stopping stale ResearchPath API process $processId."
        Stop-ProjectProcessTree -RootProcessId $processId
    }

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(10)
    do {
        if (-not (Get-NetTCPConnection -State Listen -LocalPort $apiPort -ErrorAction SilentlyContinue)) {
            return
        }
        Start-Sleep -Milliseconds 200
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    throw "旧的研径服务未能释放端口 $apiPort。"
}

function Get-EdgeExecutable {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\Application\msedge.exe')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    $command = Get-Command msedge.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw '未找到 Microsoft Edge。请安装或修复 Edge 后重试。'
}

function Get-AppEdgeProcesses {
    $escapedProfile = [Regex]::Escape($edgeProfile)
    @(
        Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and $_.CommandLine -match $escapedProfile
            }
    )
}

function Wait-ApiReady {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][string]$ErrorLog
    )

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(60)
    do {
        $Process.Refresh()
        if ($Process.HasExited) {
            $details = if (Test-Path -LiteralPath $ErrorLog) {
                (Get-Content -LiteralPath $ErrorLog -Encoding UTF8 -Tail 30) -join "`n"
            } else {
                '没有生成 API 错误日志。'
            }
            throw "本地服务启动失败。`n`n$details"
        }
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:$apiPort/api/v1/health" `
                -Method Get -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) { return }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    throw '本地服务在 60 秒内未就绪，请查看 .researchpath\logs\desktop-api.err.log。'
}

try {
    New-Item -ItemType Directory -Force -Path $stateDirectory, $edgeProfile | Out-Null
    Write-AppLog 'Desktop launcher requested.'

    $createdNew = $false
    $mutex = [Threading.Mutex]::new(
        $true,
        'Local\ResearchPath.DesktopApp',
        [ref]$createdNew
    )
    if (-not $createdNew) {
        Show-AppMessage -Message '研径已经在运行。请切换到现有窗口。' -Kind Information
        return
    }

    if (-not (Test-Path -LiteralPath $python)) {
        throw 'Python 运行环境不存在。请先运行 scripts\setup.ps1。'
    }
    if (-not (Test-Path -LiteralPath $webIndex)) {
        throw '生产界面尚未构建。请先运行 scripts\install-app.ps1。'
    }

    Clear-OwnedApiPort
    $edge = Get-EdgeExecutable

    $bootstrapBytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bootstrapBytes)
    $bootstrapToken = ([Convert]::ToBase64String($bootstrapBytes)).
        TrimEnd('=').
        Replace('+', '-').
        Replace('/', '_')
    $env:RESEARCHPATH_BOOTSTRAP_TOKEN = $bootstrapToken
    $env:RESEARCHPATH_SERVE_WEB = '1'

    $apiOutputLog = Join-Path $stateDirectory 'desktop-api.out.log'
    $apiErrorLog = Join-Path $stateDirectory 'desktop-api.err.log'
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
    Remove-Item Env:RESEARCHPATH_SERVE_WEB -ErrorAction SilentlyContinue
    Wait-ApiReady -Process $apiProcess -ErrorLog $apiErrorLog

    $launchUrl = "http://127.0.0.1:$apiPort/#bootstrap=$bootstrapToken"
    $edgeArguments = @(
        "--app=`"$launchUrl`"",
        "--user-data-dir=`"$edgeProfile`"",
        '--no-first-run',
        '--disable-background-mode',
        '--window-size=1440,960'
    )
    Start-Process -FilePath $edge -ArgumentList $edgeArguments | Out-Null
    Write-AppLog 'Desktop app window opened.'

    $edgeDeadline = [DateTimeOffset]::UtcNow.AddSeconds(15)
    do {
        $edgeProcesses = @(Get-AppEdgeProcesses)
        if ($edgeProcesses.Count -gt 0) { break }
        Start-Sleep -Milliseconds 250
    } while ([DateTimeOffset]::UtcNow -lt $edgeDeadline)
    if ($edgeProcesses.Count -eq 0) {
        throw 'Edge 应用窗口未能启动。'
    }

    while (@(Get-AppEdgeProcesses).Count -gt 0) {
        $apiProcess.Refresh()
        if ($apiProcess.HasExited) {
            throw '本地服务意外退出，请查看 .researchpath\logs\desktop-api.err.log。'
        }
        Start-Sleep -Seconds 1
    }
    Write-AppLog 'Desktop app window closed.'
}
catch {
    $launcherExitCode = 1
    Write-AppLog "Launcher error: $($_.Exception.Message)"
    Show-AppMessage -Message $_.Exception.Message -Kind Error
}
finally {
    Remove-Item Env:RESEARCHPATH_BOOTSTRAP_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:RESEARCHPATH_SERVE_WEB -ErrorAction SilentlyContinue
    if ($apiProcess) {
        $apiProcess.Refresh()
        if (-not $apiProcess.HasExited) {
            Stop-ProjectProcessTree -RootProcessId $apiProcess.Id
        }
    }
    if ($mutex) {
        try {
            $mutex.ReleaseMutex()
        }
        catch [ApplicationException] {
            # This launcher did not own the already-running instance's mutex.
        }
        $mutex.Dispose()
    }
}

if ($launcherExitCode -ne 0) {
    exit $launcherExitCode
}
