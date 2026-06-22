# Globus: aktualizace watchdog + config + restart. Spustit jako spravce.
# ASCII only

$ErrorActionPreference = "Stop"
$Task = "Mobilmajak-CameraGateway-Globus"
$Dir = "C:\ProgramData\Mobilmajak\CameraGateway-Globus"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GwDir = Join-Path $SourceDir "..\camera-gateway"

if (-not (Test-Path $GwDir)) {
    throw "Missing $GwDir - na USB musi byt camera-gateway i globus-gateway"
}
if (-not (Test-Path $Dir)) {
    throw "Gateway neni nainstalovana: $Dir - nejdriv install-globus-camera-gateway.cmd"
}

Write-Host "=== Globus: fix (camera-gateway) + restart ===" -ForegroundColor Cyan

$configUsb = Join-Path $SourceDir "config.json"
$configDir = Join-Path $Dir "config.json"
if (Test-Path $configUsb) {
    Copy-Item $configUsb $configDir -Force
    . (Join-Path $GwDir "bootstrap-python.ps1")
    $cfg = Read-GatewayConfig -Path $configDir
    Write-GatewayConfig -Path $configDir -Config $cfg
    Write-Host "Updated: config.json (z USB, UTF-8)"
} else {
    Write-Host "config.json na USB chybi - ProgramData beze zmeny" -ForegroundColor Yellow
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
Write-Host "Hotovo. Ocekavano: Supervisor start, nasloucham (bez probliknuti okna)" -ForegroundColor Green
