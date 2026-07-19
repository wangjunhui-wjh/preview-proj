@echo off
setlocal
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0desktop.ps1" logs
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0desktop.ps1" logs "%~1"
)
exit /b %ERRORLEVEL%
