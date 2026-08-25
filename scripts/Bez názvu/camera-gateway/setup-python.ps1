# Krok 1: portable Python pro branu (bez systemoveho Pythonu). ASCII only.
# Internet potreba (~25 MB). Python zustane v InstallDir.

param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-Staging"
)

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

. (Join-Path $SourceDir "bootstrap-python.ps1")

Write-Host "=== Krok 1/4: Python pro MOBILMAJAK branu ===" -ForegroundColor Cyan
Write-Host "Slozka: $InstallDir"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Copy-Item (Join-Path $SourceDir "bootstrap-python.ps1") (Join-Path $InstallDir "bootstrap-python.ps1") -Force

$py = Resolve-GatewayPython -InstallDir $InstallDir
Set-Content (Join-Path $InstallDir "python-path.txt") $py -Encoding ASCII

Write-Host ""
Write-Host "OK Python: $py" -ForegroundColor Green
Write-Host "Dalsi krok: discover-lan.cmd (nebo 02-discover-lan.cmd u prodejny)" -ForegroundColor Yellow
