# Restart main gateway task after sleep / logon (ASCII only)
param(
    [string]$TaskName = "Mobilmajak-Senimo-CameraGateway"
)

$ErrorActionPreference = "SilentlyContinue"
$logDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $logDir "gateway.log"

function Write-KickLog([string]$Message) {
    $line = "{0} wake-kick: {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-KickLog "restarting $TaskName"
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $TaskName
Write-KickLog "done"
