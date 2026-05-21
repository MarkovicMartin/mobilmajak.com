# Full deploy to https://staging.mobilmajak.com
# Usage: .\scripts\deploy-staging.ps1 [-SkipBuild]

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$VpsUser = "root"
$VpsHost = "194.182.87.138"
$StagingPath = "/home/webmajak/staging"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$BuildDir = Join-Path $Frontend "build"
$Archive = Join-Path $env:TEMP "mobilmajak-staging-backend.tar.gz"

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

Write-Host "=== Staging deploy -> https://staging.mobilmajak.com ==="
Write-Host "SSH key: $SshKey"
Write-Host ""

# 1) Backend archive (one upload)
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
& scp @sshArgs $Archive "${target}:/tmp/staging-backend.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "scp backend failed" }
Invoke-Ssh "cd $StagingPath && tar -xzf /tmp/staging-backend.tar.gz && rm -f /tmp/staging-backend.tar.gz && chown -R webmajak:webmajak $StagingPath"
Remove-Item $Archive -Force -ErrorAction SilentlyContinue
Write-Host "  OK backend"

# 2) Frontend
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
Invoke-Ssh "mkdir -p ${StagingPath}/frontend/build"
& scp @sshArgs -r "$BuildDir\*" "${target}:${StagingPath}/frontend/build/"
if ($LASTEXITCODE -ne 0) { throw "scp frontend failed" }
Write-Host "  OK frontend"

# 3) Django + services
Write-Host "[4/4] .env, collectstatic, restart ..."
$postScript = Join-Path $RepoRoot "scripts\staging-post-deploy.sh"
& scp @sshArgs $postScript "${target}:/tmp/staging-post-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "scp post-deploy script failed" }
Invoke-Ssh "sed -i 's/\r$//' /tmp/staging-post-deploy.sh; bash /tmp/staging-post-deploy.sh || true; rm -f /tmp/staging-post-deploy.sh; systemctl restart webmajak-staging; sleep 2; systemctl is-active webmajak-staging; chmod -R a+rX ${StagingPath}/frontend/build/static; systemctl reload nginx"

Write-Host ""
Write-Host "Done."
$health = (curl.exe -s -o NUL -w "%{http_code}" "https://staging.mobilmajak.com/health/" 2>$null)
Write-Host "  health: HTTP $health"
Write-Host "  https://staging.mobilmajak.com/"
