@echo off
REM Krok 2: sken site - potrebuje ConfigPath jako 1. parametr
REM Priklad: discover-lan.cmd C:\Temp\prerov-gateway\config.json
cd /d "%~dp0"
if "%~1"=="" (
  echo Pouziti: discover-lan.cmd CESTA\config.json [InstallDir]
  echo Nejdriv spustte setup-python.cmd
  pause
  exit /b 1
)
set "CFG=%~1"
set "INST=%~2"
if "%INST%"=="" set "INST=C:\ProgramData\Mobilmajak\CameraGateway-Staging"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0discover-lan.ps1" -ConfigPath "%CFG%" -InstallDir "%INST%"
if errorlevel 1 pause
