@echo off
REM Krok 3/4 - Přerov: instalace brany + test (po Kroku 1, idealne po Kroku 2)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-prerov-camera-gateway.ps1" %*
if errorlevel 1 pause
