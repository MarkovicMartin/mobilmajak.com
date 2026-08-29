@echo off
REM Prerov camera gateway install (admin)
REM Bypass Windows Restricted policy ("running scripts is disabled")
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy -Scope Process Bypass -Force; Set-ExecutionPolicy -Scope LocalMachine RemoteSigned -Force -ErrorAction SilentlyContinue; Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force -ErrorAction SilentlyContinue; Get-ChildItem -LiteralPath '%~dp0' -Filter '*.ps1' | Unblock-File; if (Test-Path '%~dp0..\camera-gateway') { Get-ChildItem -LiteralPath '%~dp0..\camera-gateway' -Filter '*.ps1' | Unblock-File }; & '%~dp0install-prerov-camera-gateway.ps1' %*"
if errorlevel 1 pause
