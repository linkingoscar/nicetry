@echo off
setlocal

set "PWSH="
for /f "delims=" %%P in ('where pwsh.exe 2^>nul') do if not defined PWSH set "PWSH=%%P"
if not defined PWSH if exist "%LOCALAPPDATA%\Programs\PowerShell\7\pwsh.exe" set "PWSH=%LOCALAPPDATA%\Programs\PowerShell\7\pwsh.exe"
if not defined PWSH (
  echo PowerShell 7 was not found. Install it or add pwsh.exe to PATH.
  pause
  exit /b 1
)

pushd "%~dp0"
"%PWSH%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-app.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
  echo.
  echo ResearchPath failed to start. See .researchpath\logs for details.
  pause
)

exit /b %EXIT_CODE%
