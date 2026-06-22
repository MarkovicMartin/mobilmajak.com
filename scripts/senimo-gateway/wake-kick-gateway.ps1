# Restart main gateway task after sleep / logon / periodic watchdog (ASCII only)
param(
    [string]$TaskName = "Mobilmajak-Senimo-CameraGateway"
)

$ErrorActionPreference = "SilentlyContinue"
$logDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $logDir "gateway.log"
$staleMinutes = 25

function Write-KickLog([string]$Message) {
    $line = "{0} wake-kick: {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

$pythonRunning = $false
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object {
        if ($_.CommandLine -like "*camera_motion_gateway*") { $script:pythonRunning = $true }
    }

$logFresh = $false
$ageMin = 9999
if (Test-Path $logFile) {
    $ageMin = ((Get-Date) - (Get-Item $logFile).LastWriteTime).TotalMinutes
    if ($ageMin -lt $staleMinutes) { $logFresh = $true }
}

if ($pythonRunning -and $logFresh) {
    Write-KickLog "skip (python running, log ${ageMin} min)"
    exit 0
}

if (-not $pythonRunning) {
    Write-KickLog "python not running -> restart $TaskName"
} elseif (-not $logFresh) {
    Write-KickLog "log stale ${ageMin} min -> restart $TaskName"
} else {
    Write-KickLog "restart $TaskName"
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $TaskName
Write-KickLog "done"
