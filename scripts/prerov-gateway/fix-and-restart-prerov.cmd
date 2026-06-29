@echo off
REM Prerov: oprava watchdog + config + restart brany (spustit jako spravce)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-and-restart-prerov.ps1"
if errorlevel 1 pause
