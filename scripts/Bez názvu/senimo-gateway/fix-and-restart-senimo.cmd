@echo off
REM Senimo: oprava watchdog + restart brany (spustit jako spravce na PC v prodejne)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-and-restart-senimo.ps1"
if errorlevel 1 pause
