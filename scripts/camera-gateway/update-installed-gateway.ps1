# Update files in C:\ProgramData\Mobilmajak\SenimoCameraGateway (no config overwrite)
# Run as admin from senimo-gateway folder:
#   powershell -ExecutionPolicy Bypass -File .\update-installed-gateway.ps1

param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\SenimoCameraGateway"
)

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskName = "Mobilmajak-Senimo-CameraGateway"

if (-not (Test-Path $InstallDir)) {
    throw "Install dir not found: $InstallDir - run install first"
}

foreach ($f in @(
    "camera_motion_gateway.py",
    "run-gateway.ps1",
    "wake-kick-gateway.ps1",
    "register-gateway-tasks.ps1",
    "bootstrap-python.ps1"
)) {
    $src = Join-Path $SourceDir $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $InstallDir $f) -Force
        Write-Host "Updated: $f"
    }
}

. (Join-Path $SourceDir "register-gateway-tasks.ps1")
Register-MobilmajakGatewayTasks `
    -TaskName $TaskName `
    -RunScript (Join-Path $InstallDir "run-gateway.ps1") `
    -WakeKickScript (Join-Path $InstallDir "wake-kick-gateway.ps1") `
    -StartupDelay "PT30S"

Write-Host "Restarting gateway..."
try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName $TaskName
Write-Host "Done. Log: $(Join-Path $InstallDir 'gateway.log')"
