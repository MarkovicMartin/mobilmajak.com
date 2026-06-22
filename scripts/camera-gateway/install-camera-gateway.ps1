# MOBILMAJAK camera gateway install (Windows, all stores)
# Python not required - installer downloads portable Python (needs internet).
#
#   .\install-camera-gateway.ps1 -ProdejnaId 2 -ProdejnaNazev Senimo

param(
    [Parameter(Mandatory = $true)]
    [int]$ProdejnaId,
    [string]$ProdejnaNazev = "Prodejna",
    [switch]$SkipTest,
    [string]$InstallDir = "",
    [string]$TaskName = ""
)

$ErrorActionPreference = "Stop"
if (-not $InstallDir) {
    $InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-$ProdejnaNazev"
}
if (-not $TaskName) {
    $TaskName = "Mobilmajak-CameraGateway-$ProdejnaNazev"
}
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

. (Join-Path $SourceDir "bootstrap-python.ps1")

Write-Host "=== MOBILMAJAK camera gateway ($ProdejnaNazev, ID $ProdejnaId) ===" -ForegroundColor Cyan

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$py = Resolve-GatewayPython -InstallDir $InstallDir
Write-Host "Python: $py"

foreach ($f in @("camera_motion_gateway.py", "run-gateway.ps1", "wake-kick-gateway.ps1", "register-gateway-tasks.ps1", "config.example.json", "bootstrap-python.ps1", "run-ps-hidden.vbs")) {
    Copy-Item (Join-Path $SourceDir $f) (Join-Path $InstallDir $f) -Force
}

$configPath = Join-Path $InstallDir "config.json"
$sourceConfig = Join-Path $SourceDir "config.json"
if (Test-Path $sourceConfig) {
    Copy-Item $sourceConfig $configPath -Force
} elseif (-not (Test-Path $configPath)) {
    Copy-Item (Join-Path $InstallDir "config.example.json") $configPath
    $cfg = Read-GatewayConfig -Path $configPath
    $cfg | Add-Member -NotePropertyName prodejna_id -NotePropertyValue $ProdejnaId -Force
    $cfg | Add-Member -NotePropertyName prodejna_nazev -NotePropertyValue $ProdejnaNazev -Force
    Write-GatewayConfig -Path $configPath -Config $cfg
    Write-Host ""
    Write-Host "Edit $configPath :" -ForegroundColor Yellow
    Write-Host "  motion_secret, nvr_pass (leave nvr_host empty for autodiscover)"
    Read-Host "Press Enter after editing config.json"
}

$cfg = Read-GatewayConfig -Path $configPath
$cfg | Add-Member -NotePropertyName prodejna_id -NotePropertyValue $ProdejnaId -Force
$cfg | Add-Member -NotePropertyName prodejna_nazev -NotePropertyValue $ProdejnaNazev -Force
if (-not $cfg.PSObject.Properties.Match('autodiscover_nvr')) {
    $cfg | Add-Member -NotePropertyName autodiscover_nvr -NotePropertyValue $true -Force
}
Write-GatewayConfig -Path $configPath -Config $cfg

foreach ($key in @("motion_secret", "nvr_pass")) {
    if ($cfg.$key -match "DOPLNTE") { throw "Missing value in config.json: $key" }
}

Set-Content (Join-Path $InstallDir "python-path.txt") $py -Encoding ASCII

. (Join-Path $SourceDir "register-gateway-tasks.ps1")
Register-MobilmajakGatewayTasks `
    -TaskName $TaskName `
    -RunScript (Join-Path $InstallDir "run-gateway.ps1") `
    -WakeKickScript (Join-Path $InstallDir "wake-kick-gateway.ps1") `
    -StartupDelay "PT30S"
Write-Host "Tasks: $TaskName + $TaskName-WakeKick" -ForegroundColor Green
Write-Host "Folder: $InstallDir"

if (-not $SkipTest) {
    Push-Location $InstallDir
    Write-Host "NVR autodiscover..."
    & $py camera_motion_gateway.py --config config.json --discover-nvr
    & $py camera_motion_gateway.py --config config.json --test-isapi
    & $py camera_motion_gateway.py --config config.json --test-motion true
    Pop-Location
}

Write-Host "Done. Log: $(Join-Path $InstallDir 'gateway.log')"
