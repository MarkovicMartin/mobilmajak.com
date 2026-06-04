@echo off
REM Instalace brany – obchazi zákaz spousteni .ps1 skriptu
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-camera-gateway.ps1" %*
if errorlevel 1 pause
