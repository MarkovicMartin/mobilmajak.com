# Odinstalace brány Senimo
param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\SenimoCameraGateway"
)

$ErrorActionPreference = "Stop"
$TaskName = "Mobilmajak-Senimo-CameraGateway"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Úloha $TaskName odstraněna."

if (Test-Path $InstallDir) {
    $remove = Read-Host "Smazat složku $InstallDir ? (a/n)"
    if ($remove -eq "a") {
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "Složka smazána."
    }
}

Write-Host "Hotovo."
