@echo off
REM Krok 1: stahne portable Python (spravce, internet)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-python.ps1" %*
if errorlevel 1 pause
