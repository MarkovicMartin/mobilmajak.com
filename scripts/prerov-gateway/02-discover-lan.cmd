@echo off
REM Krok 2/4 - Přerov: sken NVR + kamer (po Kroku 1!)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\camera-gateway\discover-lan.ps1" -ConfigPath "%~dp0config.json" -InstallDir "C:\ProgramData\Mobilmajak\CameraGateway-Prerov"
if errorlevel 1 pause
