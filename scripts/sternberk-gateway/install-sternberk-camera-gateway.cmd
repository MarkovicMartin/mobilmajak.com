@echo off
REM Sternberk camera gateway install (admin)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-sternberk-camera-gateway.ps1" %*
if errorlevel 1 pause
