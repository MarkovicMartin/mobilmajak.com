@echo off
REM Vsetin camera gateway install (admin)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-vsetin-camera-gateway.ps1" %*
if errorlevel 1 pause
