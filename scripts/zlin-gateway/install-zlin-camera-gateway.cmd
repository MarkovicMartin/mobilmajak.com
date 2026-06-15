@echo off
REM Zlin (Cepkov) camera gateway install (admin)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-zlin-camera-gateway.ps1" %*
if errorlevel 1 pause
