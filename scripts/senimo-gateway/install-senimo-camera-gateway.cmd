@echo off
REM Instalace brany Senimo – obchazi zákaz spousteni .ps1 skriptu
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-senimo-camera-gateway.ps1" %*
if errorlevel 1 pause
