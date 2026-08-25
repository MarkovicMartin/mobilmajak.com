# Krok 2: sken NVR + kamer v LAN. Vyzaduje hotovy Krok 1 (setup-python).
# ASCII only

param(
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath,
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-Staging"
)

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Chybi config: $ConfigPath"
}

$pyTxt = Join-Path $InstallDir "python-path.txt"
if (-not (Test-Path $pyTxt)) {
    throw "Nejdriv spustte setup-python.cmd (Krok 1). Chybi: $pyTxt"
}

$py = (Get-Content $pyTxt -Raw).Trim()
if (-not (Test-Path -LiteralPath $py)) {
    throw "Python nenalezen: $py - znovu spustte setup-python.cmd"
}

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Copy-Item (Join-Path $SourceDir "camera_motion_gateway.py") (Join-Path $InstallDir "camera_motion_gateway.py") -Force
Copy-Item -LiteralPath $ConfigPath (Join-Path $InstallDir "config.json") -Force

Write-Host "=== Krok 2/4: Sken site (NVR + kamery) ===" -ForegroundColor Cyan
Write-Host "Python: $py"
Write-Host "Config: $ConfigPath"
Write-Host ""

Push-Location $InstallDir
try {
    & $py camera_motion_gateway.py --config config.json --discover-lan
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Zapis IP do config.json (nvr_host, camera_host), pak Krok 3: install-*-camera-gateway.cmd" -ForegroundColor Yellow
