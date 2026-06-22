@echo off
REM Krok 1/4 - Přerov: portable Python (spravce, internet)
cd /d "%~dp0..\camera-gateway"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\camera-gateway\setup-python.ps1" -InstallDir "C:\ProgramData\Mobilmajak\CameraGateway-Prerov"
if errorlevel 1 pause
