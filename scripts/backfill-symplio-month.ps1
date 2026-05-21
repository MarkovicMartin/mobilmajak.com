# Backfill Symplio → WEB_PRODEJE_ALL (nebo SHADOW) na VPS přes backfill-historical.js
param(
    [Parameter(Mandatory = $true)]
    [string]$From,
    [Parameter(Mandatory = $true)]
    [string]$To,
    [string]$Table = "WEB_PRODEJE_ALL",
    [string]$File = "",
    [switch]$Download,
    [switch]$DryRun,
    [switch]$ShadowCompareFirst
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

$actorDir = "/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
Write-Host "Nahrávám skripty na VPS..."
scp -i $key `
    (Join-Path $RepoRoot "actors_backup\main.js") `
    (Join-Path $RepoRoot "actors_backup\backfill-historical.js") `
    (Join-Path $RepoRoot "actors_backup\compare.js") `
    "root@194.182.87.138:${actorDir}/"

$dlFlag = if ($Download) { "--download" } else { "" }
$fileFlag = if ($File) { "--file $File" } else { "" }
$dryFlag = if ($DryRun) { "--dry-run" } else { "" }

if ($ShadowCompareFirst) {
    Write-Host "=== Shadow import + compare ($From .. $To) ==="
    $shadowCmd = @"
cd $actorDir && export DB_HOST='$dbHost' DB_USER='$dbUser' DB_NAME='$dbName' DB_PASSWORD='$dbPass' PRODEJE_TABLE=WEB_PRODEJE_ALL_SHADOW && \
node import-shadow.js --file reports/symplio_${From}_${To}.xlsx 2>&1 | tail -20
"@
    ssh -i $key root@194.182.87.138 $shadowCmd
}

$remote = @"
cd $actorDir && export DB_HOST='$dbHost' DB_USER='$dbUser' DB_NAME='$dbName' DB_PASSWORD='$dbPass' PRODEJE_TABLE='$Table' && \
node backfill-historical.js --from $From --to $To $dlFlag $fileFlag $dryFlag 2>&1 | tee reports/backfill_${From}_${To}.log
"@

Write-Host "=== Backfill $From .. $To → $Table ==="
ssh -i $key root@194.182.87.138 $remote

if (-not $DryRun -and $Table -eq "WEB_PRODEJE_ALL") {
    Write-Host "=== Compare produkce ==="
    & (Join-Path $RepoRoot "scripts\compare-symplio-month.ps1") -From $From -To $To
}
