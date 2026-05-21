# Kompletní záloha actoru na VPS (bez změny produkčního main.js)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$key = Join-Path $RepoRoot ".ssh\webmajak_vps\napojeno_ed25519"
if (-not (Test-Path $key)) { throw "SSH key not found: $key" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteArchive = "/opt/backups/actor-ACTOR_FINALL_WEB_PRODEJE_ALL-$stamp.tar.gz"
$localDir = Join-Path $RepoRoot "actors_backup"
New-Item -ItemType Directory -Force -Path $localDir | Out-Null

Write-Host "=== Záloha actoru na VPS ==="
ssh -i $key root@194.182.87.138 @"
mkdir -p /opt/backups
tar -czf $remoteArchive -C /opt/actor ACTOR_FINALL_WEB_PRODEJE_ALL
ls -lh $remoteArchive
tar -tzf $remoteArchive | head -5
"@

Write-Host "Stahuji tarball..."
scp -i $key "root@194.182.87.138:${remoteArchive}" (Join-Path $localDir "actor-ACTOR_FINALL_WEB_PRODEJE_ALL-$stamp.tar.gz")
Write-Host "Hotovo: actors_backup/actor-ACTOR_FINALL_WEB_PRODEJE_ALL-$stamp.tar.gz"
