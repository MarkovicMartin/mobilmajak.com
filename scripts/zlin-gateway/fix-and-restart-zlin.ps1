# Zlin: aktualizace watchdog skriptu + restart brany. Spustit jako spravce.
# ASCII only

$ErrorActionPreference = "Stop"
$Task = "Mobilmajak-CameraGateway-Zlin"
$Dir = "C:\ProgramData\Mobilmajak\CameraGateway-Zlin"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GwDir = Join-Path $SourceDir "..\camera-gateway"

if (-not (Test-Path $Dir)) {
    throw "Gateway neni nainstalovana: $Dir - nejdriv install-zlin-camera-gateway.cmd"
}

Write-Host "=== Zlin: fix watchdog + restart ===" -ForegroundColor Cyan

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
        Copy-Item $src (Join-Path $Dir $f) -Force
        Write-Host "Updated: $f"
    }
}

. (Join-Path $Dir "register-gateway-tasks.ps1")
Register-MobilmajakGatewayTasks `
    -TaskName $Task `
    -RunScript (Join-Path $Dir "run-gateway.ps1") `
    -WakeKickScript (Join-Path $Dir "wake-kick-gateway.ps1") `
    -StartupDelay "PT30S"

Write-Host "Restarting gateway..."
Stop-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $Task
Start-Sleep -Seconds 8

Write-Host ""
Get-ScheduledTask -TaskName "$Task*" | Format-Table TaskName, State -AutoSize
$log = Join-Path $Dir "gateway.log"
if (Test-Path $log) {
    Write-Host "Log (tail):"
    Get-Content $log -Tail 15
} else {
    Write-Host "Log zatim neexistuje" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Hotovo. Ocekavano v logu: Supervisor start, nasloucham" -ForegroundColor Green
