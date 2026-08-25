@echo off
REM Camera gateway install - bypasses default .ps1 execution policy
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-camera-gateway.ps1" %*
if errorlevel 1 pause
