# MOBILMAJAK Senimo camera gateway uninstall
# ASCII only

param(
    [string]$InstallDir = "C:\ProgramData\Mobilmajak\SenimoCameraGateway"
)

$ErrorActionPreference = "Stop"
$TaskName = "Mobilmajak-Senimo-CameraGateway"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Task $TaskName removed."

if (Test-Path $InstallDir) {
    $remove = Read-Host "Delete folder $InstallDir ? (y/n)"
    if ($remove -eq "y") {
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "Folder deleted."
    }
}

Write-Host "Done."
