# Spustí compare.js na VPS (bez úpravy main.js). Pouze read + diff report.
param(
    [string]$From = "2026-04-01",
    [string]$To = "2026-04-30"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$key = Join-Path $RepoRoot ".ssh\webmajak_vps\napojeno_ed25519"
if (-not (Test-Path $key)) { throw "SSH key not found: $key" }

$envFile = Get-Content (Join-Path $RepoRoot "backend\.env") | Where-Object { $_ -match '^DB_' }
$dbPass = ($envFile | Where-Object { $_ -match '^DB_PASSWORD=' }) -replace '^DB_PASSWORD=',''
$dbHost = ($envFile | Where-Object { $_ -match '^DB_HOST=' }) -replace '^DB_HOST=',''
$dbUser = ($envFile | Where-Object { $_ -match '^DB_USER=' }) -replace '^DB_USER=',''
$dbName = ($envFile | Where-Object { $_ -match '^DB_NAME=' }) -replace '^DB_NAME=',''

$logName = "compare_${From}_${To}.log"
$remote = @"
cd /opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL && export DB_HOST='$dbHost' DB_USER='$dbUser' DB_NAME='$dbName' DB_PASSWORD='$dbPass' && node compare.js --from $From --to $To --download --out ./reports > ./reports/$logName 2>&1
"@

Write-Host "Spouštím compare na VPS ($From .. $To) ..."
ssh -i $key root@194.182.87.138 $remote

$localReports = Join-Path $RepoRoot "actors_backup\reports"
New-Item -ItemType Directory -Force -Path $localReports | Out-Null
$reportRemote = "/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/reports/compare_${From}_${To}.json"
$reportLocal = Join-Path $localReports "compare_${From}_${To}.json"
scp -i $key "root@194.182.87.138:${reportRemote}" $reportLocal
Write-Host "Report stažen: $reportLocal"
