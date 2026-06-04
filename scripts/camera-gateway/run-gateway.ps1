# MOBILMAJAK Senimo camera gateway runner (scheduled task)
# Supervisor loop - keeps gateway running, logs all output
# ASCII only

$ErrorActionPreference = "Continue"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $InstallDir

$logFile = Join-Path $InstallDir "gateway.log"
$config = Join-Path $InstallDir "config.json"
$script = Join-Path $InstallDir "camera_motion_gateway.py"
$restartSeconds = 30

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function Format-Line($Item) {
    if ($null -eq $Item) { return "" }
    if ($Item -is [System.Management.Automation.ErrorRecord]) {
        return $Item.ToString()
    }
    return $Item.ToString()
}

if (-not (Test-Path $config)) {
    Write-Log "ERROR: missing config.json"
    exit 1
}

if (-not (Test-Path $script)) {
    Write-Log "ERROR: missing camera_motion_gateway.py"
    exit 1
}

$pythonExe = $null
$marker = Join-Path $InstallDir "python-path.txt"
if (Test-Path $marker) {
    $pythonExe = (Get-Content $marker -Raw).Trim()
}
if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    $embedded = Join-Path $InstallDir "python-embed\python.exe"
    if (Test-Path $embedded) { $pythonExe = $embedded }
}
if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonExe = (& py -3 -c "import sys; print(sys.executable)" 2>$null).Trim()
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonExe = (& python -c "import sys; print(sys.executable)" 2>$null).Trim()
    }
}

if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    Write-Log "ERROR: Python not found"
    exit 1
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
Write-Log "Supervisor start (python=$pythonExe)"

while ($true) {
    Write-Log "Starting gateway worker..."
    try {
        & $pythonExe $script --config $config 2>&1 | ForEach-Object {
            $text = Format-Line $_
            if ($text) { Write-Log $text }
        }
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        Write-Log "Gateway worker exited (code $code)"
    } catch {
        Write-Log ("Gateway worker exception: " + $_.Exception.Message)
    }
    Write-Log "Restart in ${restartSeconds}s..."
    Start-Sleep -Seconds $restartSeconds
}
