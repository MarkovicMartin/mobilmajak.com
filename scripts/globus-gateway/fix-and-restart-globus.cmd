@echo off
REM Globus: oprava watchdog + config + restart brany (spustit jako spravce)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-and-restart-globus.ps1"
if errorlevel 1 pause
