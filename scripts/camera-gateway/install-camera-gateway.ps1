# Instalace brány pohybu kamer → MOBILMAJAK (Windows, všechny prodejny)
# Python NENÍ potřeba – instalátor stáhne portable Python sám (internet).
#
#   .\install-camera-gateway.ps1 -ProdejnaId 2 -ProdejnaNazev Senimo

param(
    [Parameter(Mandatory = $true)]
    [int]$ProdejnaId,
    [string]$ProdejnaNazev = "Prodejna",
    [switch]$SkipTest,
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"
if (-not $InstallDir) {
    $InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-$ProdejnaNazev"
}
$TaskName = "Mobilmajak-CameraGateway-$ProdejnaNazev"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

. (Join-Path $SourceDir "bootstrap-python.ps1")

Write-Host "=== MOBILMAJAK – brána kamer ($ProdejnaNazev, ID $ProdejnaId) ===" -ForegroundColor Cyan

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$py = Resolve-GatewayPython -InstallDir $InstallDir
Write-Host "Python: $py"

foreach ($f in @("camera_motion_gateway.py", "run-gateway.ps1", "wake-kick-gateway.ps1", "register-gateway-tasks.ps1", "config.example.json", "bootstrap-python.ps1")) {
    Copy-Item (Join-Path $SourceDir $f) (Join-Path $InstallDir $f) -Force
}

$configPath = Join-Path $InstallDir "config.json"
$sourceConfig = Join-Path $SourceDir "config.json"
if (Test-Path $sourceConfig) {
    Copy-Item $sourceConfig $configPath -Force
} elseif (-not (Test-Path $configPath)) {
    Copy-Item (Join-Path $InstallDir "config.example.json") $configPath
    $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
    $cfg.prodejna_id = $ProdejnaId
    $cfg.prodejna_nazev = $ProdejnaNazev
    $cfg | ConvertTo-Json -Depth 5 | Set-Content $configPath -Encoding UTF8
    Write-Host ""
    Write-Host "Upravte $configPath :" -ForegroundColor Yellow
    Write-Host "  motion_secret, nvr_pass (nvr_host nechte prázdné = autodetekce)"
    Read-Host "Po úpravě Enter"
}

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$cfg.prodejna_id = $ProdejnaId
$cfg.prodejna_nazev = $ProdejnaNazev
if (-not $cfg.autodiscover_nvr) { $cfg | Add-Member -NotePropertyName autodiscover_nvr -NotePropertyValue $true -Force }
$cfg | ConvertTo-Json -Depth 5 | Set-Content $configPath -Encoding UTF8

foreach ($key in @("motion_secret", "nvr_pass")) {
    if ($cfg.$key -match "DOPLNTE") { throw "V config.json doplňte: $key" }
}

Set-Content (Join-Path $InstallDir "python-path.txt") $py -Encoding UTF8

. (Join-Path $SourceDir "register-gateway-tasks.ps1")
Register-MobilmajakGatewayTasks `
    -TaskName $TaskName `
    -RunScript (Join-Path $InstallDir "run-gateway.ps1") `
    -WakeKickScript (Join-Path $InstallDir "wake-kick-gateway.ps1") `
    -StartupDelay "PT30S"
Write-Host "Tasks: $TaskName + $TaskName-WakeKick" -ForegroundColor Green
Write-Host "Složka: $InstallDir"

if (-not $SkipTest) {
    Push-Location $InstallDir
    Write-Host "Autodetekce NVR…"
    & $py camera_motion_gateway.py --config config.json --discover-nvr
    & $py camera_motion_gateway.py --config config.json --test-isapi
    & $py camera_motion_gateway.py --config config.json --test-motion true
    Pop-Location
}

Write-Host "Hotovo. Log: $(Join-Path $InstallDir 'gateway.log')"
