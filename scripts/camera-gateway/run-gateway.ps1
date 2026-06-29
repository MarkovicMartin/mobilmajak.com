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

function Test-PythonGatewayUsable {
    param([string]$Exe)

    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $Exe -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 8) else 1)" 2>$null | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

$pythonExe = $null
$marker = Join-Path $InstallDir "python-path.txt"
if (Test-Path $marker) {
    $candidate = (Get-Content $marker -Raw).Trim()
    if (Test-PythonGatewayUsable $candidate) { $pythonExe = $candidate }
}
$embedded = Join-Path $InstallDir "python-embed\python.exe"
if (Test-PythonGatewayUsable $embedded) { $pythonExe = $embedded }

if (-not $pythonExe) {
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
