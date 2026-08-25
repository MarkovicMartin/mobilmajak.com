# MOBILMAJAK Senimo camera gateway installer
# Requires scripts/camera-gateway on the same machine (copy both folders to USB).
# ASCII only

param(
    [switch]$SkipTest,
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\SenimoCameraGateway"
)

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GwDir = Join-Path $SourceDir "..\camera-gateway"
$GwInstall = Join-Path $GwDir "install-camera-gateway.ps1"

if (-not (Test-Path $GwInstall)) {
    throw "Missing $GwInstall - copy scripts/camera-gateway next to senimo-gateway"
}

$configLocal = Join-Path $SourceDir "config.json"
$configExample = Join-Path $SourceDir "config.example.json"
if (-not (Test-Path $configLocal)) {
    if (Test-Path $configExample) {
        Copy-Item $configExample $configLocal
        Write-Host "Created config.json from example - set motion_secret and nvr_pass" -ForegroundColor Yellow
    } else {
        throw "Missing config.json and config.example.json in $SourceDir"
    }
}

Copy-Item $configLocal (Join-Path $GwDir "config.json") -Force

$installArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $GwInstall,
    "-ProdejnaId", "2",
    "-ProdejnaNazev", "Senimo",
    "-InstallDir", $InstallDir,
    "-TaskName", "Mobilmajak-Senimo-CameraGateway"
)
if ($SkipTest) { $installArgs += "-SkipTest" }

& powershell.exe @installArgs
