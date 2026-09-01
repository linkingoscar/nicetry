[CmdletBinding()]
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$launcher = Join-Path $PSScriptRoot 'start-app.ps1'
$sourceIcon = Join-Path $root 'assets\branding\researchpath.ico'
$webIndex = Join-Path $root 'apps\web\dist\index.html'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python 运行环境不存在。请先运行 scripts\setup.ps1。'
}
if (-not (Test-Path -LiteralPath $sourceIcon)) {
    throw "应用图标不存在：$sourceIcon"
}

if (-not $SkipBuild) {
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    & $npm run build:web
    if ($LASTEXITCODE -ne 0) {
        throw '生产界面构建失败。'
    }
}
if (-not (Test-Path -LiteralPath $webIndex)) {
    throw '生产界面不存在；请移除 -SkipBuild 后重新安装。'
}

$pwsh = Join-Path $PSHOME 'pwsh.exe'
if (-not (Test-Path -LiteralPath $pwsh)) {
    throw '当前环境不是 PowerShell 7，无法生成可靠的桌面启动入口。'
}

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
$shortcutPath = Join-Path $desktop '研径 ResearchPath.lnk'
$iconHash = (Get-FileHash -LiteralPath $sourceIcon -Algorithm SHA256).Hash.
    Substring(0, 12).
    ToLowerInvariant()
$installedIconDirectory = Join-Path $root '.researchpath\app-icons'
$installedIcon = Join-Path $installedIconDirectory "researchpath-$iconHash.ico"
New-Item -ItemType Directory -Force -Path $installedIconDirectory | Out-Null
Copy-Item -LiteralPath $sourceIcon -Destination $installedIcon -Force

if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pwsh
$shortcut.Arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = "$installedIcon,0"
$shortcut.Description = '研径 ResearchPath 本地实证研究工作台'
$shortcut.WindowStyle = 7
$shortcut.Save()

if (-not ('ResearchPathShellChange' -as [type])) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ResearchPathShellChange
{
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(
        uint eventId,
        uint flags,
        IntPtr item1,
        IntPtr item2
    );
}
'@
}
[ResearchPathShellChange]::SHChangeNotify(
    0x08000000,
    0,
    [IntPtr]::Zero,
    [IntPtr]::Zero
)

Write-Host "桌面快捷方式已创建：$shortcutPath" -ForegroundColor Green
Write-Host '以后双击图标即可打开；关闭应用窗口后，本地服务会自动退出。' -ForegroundColor Cyan
