# MOBILMAJAK Senimo camera gateway installer (Windows)
# ASCII only - safe for Windows PowerShell 5.1 encoding
#
#   powershell -ExecutionPolicy Bypass -File .\install-senimo-camera-gateway.ps1

param(
    [switch]$SkipTest,
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\SenimoCameraGateway"
)

$ErrorActionPreference = "Stop"
$TaskName = "Mobilmajak-Senimo-CameraGateway"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$bootstrapPath = Join-Path $SourceDir "bootstrap-python.ps1"
if (Test-Path $bootstrapPath) {
    . $bootstrapPath
} else {
    function Resolve-GatewayPython {
        param([Parameter(Mandatory = $true)][string]$InstallDir)
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $v = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) { return $v.Trim() }
        }
        foreach ($name in @("python3", "python")) {
            if (Get-Command $name -ErrorAction SilentlyContinue) {
                $v = & $name -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $v) { return $v.Trim() }
            }
        }
        throw "Python not found. Install Python or copy senimo-gateway folder with bootstrap-python.ps1"
    }
}

Write-Host "=== MOBILMAJAK Senimo camera gateway install ===" -ForegroundColor Cyan

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$pyExe = Resolve-GatewayPython -InstallDir $InstallDir
Write-Host "Python: $pyExe"

Write-Host "Installing requests..."
& $pyExe -m pip install --upgrade pip requests | Out-Host
if ($LASTEXITCODE -ne 0) { throw "pip install requests failed" }

$files = @(
    "camera_motion_gateway.py",
    "run-gateway.ps1",
    "config.example.json"
)
if (Test-Path $bootstrapPath) { $files += "bootstrap-python.ps1" }
foreach ($f in $files) {
    Copy-Item -Path (Join-Path $SourceDir $f) -Destination (Join-Path $InstallDir $f) -Force
}

$configPath = Join-Path $InstallDir "config.json"
$sourceConfig = Join-Path $SourceDir "config.json"
if (Test-Path $sourceConfig) {
    Copy-Item $sourceConfig $configPath -Force
    Write-Host "Using config.json from install folder." -ForegroundColor Green
} elseif (-not (Test-Path $configPath)) {
    Copy-Item (Join-Path $InstallDir "config.example.json") $configPath
    Write-Host ""
    Write-Host "WARNING: Edit $configPath" -ForegroundColor Yellow
    Write-Host "  - motion_secret (same as staging VPS)"
    Write-Host "  - nvr_pass (NVR admin password)"
    Write-Host ""
    Read-Host "Press Enter after editing config.json"
}

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
foreach ($key in @("motion_secret", "nvr_pass")) {
    if ($cfg.$key -match "DOPLNTE") {
        throw "Missing value in config.json: $key"
    }
}

Set-Content -Path (Join-Path $InstallDir "python-path.txt") -Value $pyExe -Encoding ASCII

$runScript = Join-Path $InstallDir "run-gateway.ps1"
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runScript`""

$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT2M"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -RestartCount 999

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "Scheduled task: $TaskName (startup + 2 min delay)" -ForegroundColor Green

if (-not $SkipTest) {
    Write-Host ""
    Write-Host "NVR autodiscover..."
    Push-Location $InstallDir
    & $pyExe camera_motion_gateway.py --config config.json --discover-nvr
    Write-Host "ISAPI test..."
    & $pyExe camera_motion_gateway.py --config config.json --test-isapi
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ISAPI test failed - check network and config.json" -ForegroundColor Yellow
    } else {
        Write-Host "Staging motion test..."
        & $pyExe camera_motion_gateway.py --config config.json --test-motion true
    }
    Pop-Location
}

Write-Host ""
Write-Host "Install done." -ForegroundColor Green
Write-Host "Folder: $InstallDir"
Write-Host "Log:    $(Join-Path $InstallDir 'gateway.log')"
Write-Host ""
Write-Host "Start now:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
