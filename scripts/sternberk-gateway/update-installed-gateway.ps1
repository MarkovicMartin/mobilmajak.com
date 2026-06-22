# Update Sternberk gateway files in ProgramData (no config overwrite)

param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-Sternberk"
)

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GwDir = Join-Path $SourceDir "..\camera-gateway"
$TaskName = "Mobilmajak-CameraGateway-Sternberk"

if (-not (Test-Path $InstallDir)) {
    throw "Install dir not found: $InstallDir - run install first"
}

foreach ($f in @(
    "camera_motion_gateway.py",
    "run-gateway.ps1",
    "wake-kick-gateway.ps1",
    "register-gateway-tasks.ps1",
    "bootstrap-python.ps1",
    "run-ps-hidden.vbs"
)) {
    $src = Join-Path $GwDir $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $InstallDir $f) -Force
        Write-Host "Updated: $f"
    }
}

. (Join-Path $InstallDir "register-gateway-tasks.ps1")
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
