@echo off
REM Globus: sken NVR + kamer v LAN (volitelne pred instalaci)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\camera-gateway\discover-lan.ps1" -ConfigPath "%~dp0config.json" -InstallDir "C:\ProgramData\Mobilmajak\CameraGateway-Globus"
if errorlevel 1 pause
