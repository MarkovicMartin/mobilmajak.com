# Full deploy to https://mobilmajak.com (produkce)
# Usage: .\scripts\deploy-production.ps1 [-SkipBuild]

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$VpsUser = "root"
$VpsHost = "194.182.87.138"
$ProdPath = "/home/webmajak/webapp"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$BuildDir = Join-Path $Frontend "build"
$Archive = Join-Path $env:TEMP "mobilmajak-production-backend.tar.gz"

$defaultKey = Join-Path $RepoRoot ".ssh\webmajak_vps\napojeno_ed25519"
$SshKey = if ($env:SSH_KEY -and (Test-Path $env:SSH_KEY)) { $env:SSH_KEY }
          elseif (Test-Path $defaultKey) { $defaultKey }
          else { "$env:USERPROFILE\.ssh\napojeno_ed25519" }

if (-not (Test-Path $SshKey)) { throw "SSH key not found: $SshKey" }

$sshArgs = @("-i", $SshKey, "-o", "StrictHostKeyChecking=accept-new")
$target = "${VpsUser}@${VpsHost}"

function Invoke-Ssh([string]$Cmd) {
    & ssh @sshArgs $target $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH failed: $Cmd" }
}

Write-Host "=== Production deploy -> https://mobilmajak.com ==="
Write-Host "SSH key: $SshKey"
Write-Host ""

Write-Host "[1/4] Packing backend ..."
if (Test-Path $Archive) { Remove-Item $Archive -Force }
Push-Location $Backend
try {
    & tar -czf $Archive `
        --exclude=venv `
        --exclude=__pycache__ `
        --exclude=*.pyc `
        --exclude=logs `
        --exclude=media `
        --exclude=staticfiles `
        .
    if ($LASTEXITCODE -ne 0) { throw "tar pack failed" }
} finally {
    Pop-Location
}
$sizeMb = [math]::Round((Get-Item $Archive).Length / 1MB, 1)
Write-Host "  archive ${sizeMb} MB"

Write-Host "[2/4] Upload backend + extract ..."
& scp @sshArgs $Archive "${target}:/tmp/production-backend.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "scp backend failed" }
Invoke-Ssh "cd $ProdPath && tar -xzf /tmp/production-backend.tar.gz && rm -f /tmp/production-backend.tar.gz && chown -R webmajak:webmajak $ProdPath"
Remove-Item $Archive -Force -ErrorAction SilentlyContinue
Write-Host "  OK backend"

if (-not $SkipBuild) {
    Write-Host "[3/4] npm run build ..."
    Push-Location $Frontend
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
    } finally {
        Pop-Location
    }
} elseif (-not (Test-Path (Join-Path $BuildDir "index.html"))) {
    throw "Missing $BuildDir - run without -SkipBuild"
}

Write-Host "[3/4] Upload frontend build ..."
Invoke-Ssh "mkdir -p ${ProdPath}/frontend/build"
& scp @sshArgs -r "$BuildDir\*" "${target}:${ProdPath}/frontend/build/"
if ($LASTEXITCODE -ne 0) { throw "scp frontend failed" }
Write-Host "  OK frontend"

Write-Host "[4/4] collectstatic, restart ..."
$postScript = Join-Path $RepoRoot "scripts\production-post-deploy.sh"
& scp @sshArgs $postScript "${target}:/tmp/production-post-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "scp post-deploy script failed" }
Invoke-Ssh "sed -i 's/\r$//' /tmp/production-post-deploy.sh; bash /tmp/production-post-deploy.sh || true; rm -f /tmp/production-post-deploy.sh; chmod -R a+rX ${ProdPath}/frontend/build/static; systemctl reload nginx"

Write-Host ""
Write-Host "Done."
$health = (curl.exe -s -o NUL -w "%{http_code}" "https://mobilmajak.com/health/" 2>$null)
Write-Host "  health: HTTP $health"
Write-Host "  https://mobilmajak.com/"
