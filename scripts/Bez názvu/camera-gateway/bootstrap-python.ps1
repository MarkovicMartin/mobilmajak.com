# Portable Python 3.12 for gateway (no system Python install)
# ASCII only

function Get-GatewayCacheDir {
    param([string]$InstallDir = "C:\ProgramData\Mobilmajak\CameraGateway-Cache")

    if ($InstallDir) {
        $cache = Join-Path $InstallDir "_cache"
    } else {
        $cache = "C:\ProgramData\Mobilmajak\CameraGateway-Cache"
    }
    if (-not (Test-Path $cache)) {
        New-Item -ItemType Directory -Path $cache -Force | Out-Null
    }
    return $cache
}

function Remove-GatewayTempFile {
    param([string]$Path)
    if (-not $Path) { return }
    try {
        if ([System.IO.File]::Exists($Path)) {
            [System.IO.File]::Delete($Path)
        }
    } catch {
        Write-Host "Warning: could not delete temp file $Path" -ForegroundColor Yellow
    }
}

function Invoke-GatewayPythonQuiet {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string[]]$PyArgs
    )

    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $null = & $PythonExe @PyArgs 2>&1
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 1 }
    $ErrorActionPreference = $prev
    return $code
}

function Test-GatewayPythonImport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [string]$ModuleName = 'requests'
    )

    return (Invoke-GatewayPythonQuiet -PythonExe $PythonExe -PyArgs @('-c', "import $ModuleName")) -eq 0
}

function Ensure-GatewayPythonDeps {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [string]$InstallDir = ""
    )

    if (Test-GatewayPythonImport -PythonExe $PythonExe) { return $true }

    Write-Host "Installing requests for gateway Python..."
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $PythonExe -m pip install --upgrade pip requests | Out-Host
    $pipCode = $LASTEXITCODE
    $ErrorActionPreference = $prev

    if ($pipCode -eq 0 -and (Test-GatewayPythonImport -PythonExe $PythonExe)) {
        return $true
    }

    if ($InstallDir) {
        $embedDir = Join-Path $InstallDir "python-embed"
        Write-Host "Broken embedded Python - removing $embedDir" -ForegroundColor Yellow
        if (Test-Path -LiteralPath $embedDir) {
            Remove-Item -LiteralPath $embedDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        return $false
    }

    throw "pip install requests failed"
}

function Install-EmbeddedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetDir
    )

    $version = "3.12.8"
    $embedDir = Join-Path $TargetDir "python-embed"
    $cacheDir = Get-GatewayCacheDir -InstallDir $TargetDir
    $zipPath = Join-Path $cacheDir "mobilmajak-python-embed.zip"
    $url = "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip"

    if (-not (Test-Path $embedDir)) {
        New-Item -ItemType Directory -Path $embedDir -Force | Out-Null
    }

    $pythonExe = Join-Path $embedDir "python.exe"
    if (Test-Path -LiteralPath $pythonExe) {
        Write-Host "Reusing embedded Python: $pythonExe" -ForegroundColor Green
        if (Ensure-GatewayPythonDeps -PythonExe $pythonExe -InstallDir $TargetDir) {
            return $pythonExe
        }
        Write-Host "Re-downloading embedded Python..." -ForegroundColor Yellow
    }

    Write-Host "Downloading portable Python $version (~25 MB)..." -ForegroundColor Yellow
    Write-Host "URL: $url"
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    Expand-Archive -LiteralPath $zipPath -DestinationPath $embedDir -Force
    Remove-GatewayTempFile -Path $zipPath

    if (-not (Test-Path $pythonExe)) {
        throw "Missing $pythonExe after extract"
    }

    $pthFile = Get-ChildItem -Path $embedDir -Filter "python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $pthContent = @(
            "python312.zip",
            ".",
            "Lib\site-packages",
            "",
            "# Enable site",
            "import site"
        )
        Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ASCII
    }

    New-Item -ItemType Directory -Path (Join-Path $embedDir "Lib\site-packages") -Force | Out-Null

    $getPip = Join-Path $cacheDir "get-pip.py"
    Write-Host "Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    & $pythonExe $getPip --no-warn-script-location | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed" }
    Remove-GatewayTempFile -Path $getPip

    Write-Host "Installing requests..."
    & $pythonExe -m pip install --upgrade pip requests | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "pip install requests failed" }

    Write-Host "Portable Python ready: $pythonExe" -ForegroundColor Green
    return $pythonExe
}

function Test-GatewayPythonExe {
    param([string]$Exe)

    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $null }
    # Windows Store alias (python.exe / python3.exe) - not a real install
    if ($Exe -match '\\WindowsApps\\') { return $null }

    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'SilentlyContinue'
        $v = & $Exe -c "import sys; print(sys.executable)" 2>$null
        $ErrorActionPreference = $prev
        if ($LASTEXITCODE -eq 0 -and $v) {
            $path = $v.Trim()
            if (Test-Path -LiteralPath $path) { return $path }
        }
    } catch {
        return $null
    }
    return $null
}

function Test-GatewayPythonMinVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [int]$MinMajor = 3,
        [int]$MinMinor = 8
    )

    $check = "import sys; sys.exit(0 if sys.version_info[:2] >= ($MinMajor, $MinMinor) else 1)"
    return (Invoke-GatewayPythonQuiet -PythonExe $PythonExe -PyArgs @('-c', $check)) -eq 0
}

function Resolve-GatewayPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallDir
    )

    $embedExe = Join-Path $InstallDir "python-embed\python.exe"
    if (Test-Path -LiteralPath $embedExe) {
        if ((Test-GatewayPythonMinVersion -PythonExe $embedExe) -and
            (Test-GatewayPythonImport -PythonExe $embedExe)) {
            return $embedExe
        }
    }

    Write-Host "Using portable Python 3.12 (system Python < 3.8 is not supported)..." -ForegroundColor Yellow
    return Install-EmbeddedPython -TargetDir $InstallDir
}

function Read-GatewayConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $utf8 = New-Object System.Text.UTF8Encoding $false
    $text = [System.IO.File]::ReadAllText($Path, $utf8)
    if ($text.Length -gt 0 -and [int][char]$text[0] -eq 0xFEFF) {
        $text = $text.Substring(1)
    }
    return ($text | ConvertFrom-Json)
}

function Write-GatewayConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    $json = $Config | ConvertTo-Json -Depth 5
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $json, $utf8)
}
