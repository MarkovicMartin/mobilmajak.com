# MOBILMAJAK Prerov camera gateway uninstall

param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-Prerov"
)

$ErrorActionPreference = "Stop"
$TaskName = "Mobilmajak-CameraGateway-Prerov"

Unregister-ScheduledTask -TaskName "$TaskName-WakeKick" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Tasks removed."

if (Test-Path $InstallDir) {
    $remove = Read-Host "Delete folder $InstallDir ? (y/n)"
    if ($remove -eq "y") {
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "Folder deleted."
    }
}

Write-Host "Done."
