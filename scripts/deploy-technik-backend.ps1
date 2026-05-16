# Nasazení technik_utils + views na VPS (vyžaduje SSH klíč)
# Použití:
#   $env:SSH_KEY = "$env:USERPROFILE\.ssh\napojeno_ed25519"
#   .\scripts\deploy-technik-backend.ps1
#
# Nebo s heslem / jiným uživatelem:
#   $env:VPS_USER = "root"
#   $env:VPS_HOST = "80.211.198.189"

$ErrorActionPreference = "Stop"
$VpsUser = if ($env:VPS_USER) { $env:VPS_USER } else { "webmajak" }
$VpsHost = if ($env:VPS_HOST) { $env:VPS_HOST } else { "194.182.87.138" }
$VpsPath = "/home/webmajak/webapp"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $RepoRoot "backend"
$SshKey = $env:SSH_KEY

$sshArgs = @("-o", "StrictHostKeyChecking=accept-new")
if ($SshKey -and (Test-Path $SshKey)) {
    $sshArgs = @("-i", $SshKey) + $sshArgs
} elseif ($SshKey) {
    Write-Error "SSH klíč neexistuje: $SshKey"
}

$files = @(
    "analytics/technik_utils.py",
    "analytics/views.py",
    "users/management/commands/populate_technik_id.py"
)

Write-Host "Nahrávám soubory na ${VpsUser}@${VpsHost}:${VpsPath} ..."
foreach ($rel in $files) {
    $local = Join-Path $Backend $rel
    if (-not (Test-Path $local)) { throw "Chybí soubor: $local" }
    $remoteDir = "$VpsPath/" + (Split-Path $rel -Parent)
    & ssh @sshArgs "${VpsUser}@${VpsHost}" "mkdir -p $remoteDir"
    & scp @sshArgs $local "${VpsUser}@${VpsHost}:${VpsPath}/$($rel -replace '\\','/')"
    Write-Host "  OK $rel"
}

Write-Host "Restartuji webmajak ..."
& ssh @sshArgs "${VpsUser}@${VpsHost}" "sudo systemctl restart webmajak && sudo systemctl is-active webmajak"
Write-Host "Hotovo."
Write-Host "Ověřte API (po přihlášení): https://staging.mobilmajak.com/analytics/servis"
Write-Host ""
Write-Host "Alternativa (git na serveru):"
Write-Host "  ssh ... `"cd $VpsPath && git pull origin main && sudo systemctl restart webmajak`""
