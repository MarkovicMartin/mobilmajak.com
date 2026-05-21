# Local full-stack test: Django (DB) + production build + browser
# Usage: .\scripts\run-local.ps1
#        .\scripts\run-local.ps1 -Rebuild

param(
    [switch]$Rebuild,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 8001
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'
$BuildDir = Join-Path $FrontendDir 'build'
$VenvDir = Join-Path $BackendDir 'venv'
$EnvFile = Join-Path $BackendDir '.env'
$EnvExample = Join-Path $BackendDir '.env.example'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$FrontendUrl = "http://localhost:$FrontendPort"
$BackendUrl = "http://127.0.0.1:$BackendPort"

function Write-Step([string]$Msg) { Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok([string]$Msg) { Write-Host "OK  $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "!!  $Msg" -ForegroundColor Yellow }

function Stop-Port([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}

function Wait-HttpOk([string]$Url, [int]$MaxSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function Ensure-EnvFile {
    if (-not (Test-Path $EnvExample)) {
        throw "Missing $EnvExample"
    }
    if (-not (Test-Path $EnvFile)) {
        Copy-Item $EnvExample $EnvFile
        Write-Warn "Created $EnvFile from .env.example"
    }

    if ($env:DB_PASSWORD) {
        $lines = Get-Content $EnvFile
        $updated = $false
        $newLines = foreach ($line in $lines) {
            if ($line -match '^\s*DB_PASSWORD=') {
                $updated = $true
                "DB_PASSWORD=$env:DB_PASSWORD"
            } else {
                $line
            }
        }
        if (-not $updated) {
            $newLines = @($newLines) + "DB_PASSWORD=$env:DB_PASSWORD"
        }
        Set-Content -Path $EnvFile -Value $newLines -Encoding UTF8
        Write-Ok 'DB_PASSWORD from environment variable'
    }

    $pwLine = Get-Content $EnvFile | Where-Object { $_ -match '^\s*DB_PASSWORD=' } | Select-Object -First 1
    if (-not $pwLine -or $pwLine -match '^\s*DB_PASSWORD=\s*$') {
        throw @"
backend\.env is missing DB_PASSWORD (MySQL on Webglobe).
Set it once in backend\.env or run:
  `$env:DB_PASSWORD = 'your-password'; .\scripts\run-local.ps1
"@
    }
}

function Ensure-PythonVenv {
    if (-not (Test-Path $PythonExe)) {
        Write-Step 'Creating Python venv ...'
        $py = Get-Command python -ErrorAction SilentlyContinue
        if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
        if (-not $py) { throw 'Python not in PATH. Install Python 3.10+.' }

        if ($py.Name -eq 'py') {
            & py -3 -m venv $VenvDir
        } else {
            & python -m venv $VenvDir
        }
    }

    Write-Step 'Installing Python dependencies (may take a while) ...'
    & $PythonExe -m pip install -q --upgrade pip
    & $PythonExe -m pip install -q -r (Join-Path $BackendDir 'requirements.txt')
}

function Ensure-FrontendBuild {
    if ($Rebuild -or -not (Test-Path (Join-Path $BuildDir 'index.html'))) {
        Write-Step 'Building frontend (npm run build) ...'
        Push-Location $FrontendDir
        try {
            if (-not (Test-Path 'node_modules')) {
                npm install
            }
            npm run build
            if ($LASTEXITCODE -ne 0) { throw 'npm run build failed' }
        } finally {
            Pop-Location
        }
    } else {
        Write-Ok 'Using existing frontend/build (-Rebuild for fresh build)'
    }
}

function Test-Database {
    Write-Step 'Checking database connection ...'
    Push-Location $BackendDir
    $prevEap = $ErrorActionPreference
    try {
        # Django warnings go to stderr; with Stop that would abort before we read $LASTEXITCODE
        $ErrorActionPreference = 'Continue'
        & $PythonExe manage.py check --database default 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Django check failed - see backend\.env' }
    } finally {
        $ErrorActionPreference = $prevEap
        Pop-Location
    }
}

$djangoProc = $null
$frontendProc = $null

Write-Host ''
Write-Host 'MOBILMAJAK - local test (build + DB + API)' -ForegroundColor White
Write-Host "Repo: $RepoRoot"

try {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw 'Node.js not in PATH.'
    }

    Ensure-EnvFile
    Ensure-PythonVenv
    Ensure-FrontendBuild
    Test-Database

    Write-Step "Freeing ports $BackendPort and $FrontendPort ..."
    Stop-Port $BackendPort
    Stop-Port $FrontendPort
    Start-Sleep -Seconds 1

    Write-Step "Starting Django API on port $BackendPort ..."
    $djangoProc = Start-Process -FilePath $PythonExe `
        -ArgumentList 'manage.py', 'runserver', "127.0.0.1:$BackendPort", '--noreload' `
        -WorkingDirectory $BackendDir `
        -PassThru `
        -WindowStyle Hidden

    if (-not (Wait-HttpOk "$BackendUrl/health/")) {
        throw "Backend at $BackendUrl not responding. Check DB_PASSWORD and network."
    }
    Write-Ok "Backend running ($BackendUrl)"

    Write-Step "Starting frontend build on port $FrontendPort ..."
    $env:API_PROXY = $BackendUrl
    $env:PORT = "$FrontendPort"
    $frontendProc = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', 'npm run serve:build' `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Hidden

    if (-not (Wait-HttpOk "$FrontendUrl/")) {
        throw "Frontend at $FrontendUrl not responding."
    }
    Write-Ok "Frontend running ($FrontendUrl)"

    Write-Step 'Opening browser ...'
    Start-Process $FrontendUrl

    Write-Host ''
    Write-Host '========================================' -ForegroundColor Green
    Write-Host "  App:       $FrontendUrl"
    Write-Host "  API/DB:    $BackendUrl  (MySQL via backend/.env)"
    Write-Host '  Stop:      Ctrl+C in this window'
    Write-Host '========================================' -ForegroundColor Green
    Write-Host ''

    while (-not $djangoProc.HasExited -and -not $frontendProc.HasExited) {
        Start-Sleep -Seconds 2
    }

    if ($djangoProc.HasExited) { Write-Warn "Django exited (code $($djangoProc.ExitCode))" }
    if ($frontendProc.HasExited) { Write-Warn "Frontend exited (code $($frontendProc.ExitCode))" }
}
catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Write-Step 'Stopping processes ...'
    foreach ($p in @($djangoProc, $frontendProc)) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Stop-Port $BackendPort
    Stop-Port $FrontendPort
}
