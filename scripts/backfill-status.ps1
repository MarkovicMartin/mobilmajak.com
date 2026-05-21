# Stav backfillu na VPS (2024-01 .. 2026-03)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$key = Join-Path $RepoRoot ".ssh\webmajak_vps\napojeno_ed25519"
$actor = "/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"

Write-Host "=== Backfill log (tail) ==="
ssh -i $key root@194.182.87.138 "tail -25 $actor/reports/backfill_2024-01_2026-03.log"

Write-Host "`n=== Proces ==="
ssh -i $key root@194.182.87.138 "pgrep -af 'backfill-months|backfill-historical' || echo '(zadny backfill proces)'"

Write-Host "`n=== Cron ==="
ssh -i $key root@194.182.87.138 "crontab -l | grep -i prodeje || echo '(cron prodeje nenalezen)'"
