@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-globus-camera-gateway.ps1" %*
if errorlevel 1 pause
