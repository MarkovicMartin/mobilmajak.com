# Portable Python 3.12 for gateway (no system Python install)
# ASCII only

function Install-EmbeddedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetDir
    )

    $version = "3.12.8"
    $embedDir = Join-Path $TargetDir "python-embed"
    $zipPath = Join-Path $env:TEMP "mobilmajak-python-embed.zip"
    $url = "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip"

    if (-not (Test-Path $embedDir)) {
        New-Item -ItemType Directory -Path $embedDir -Force | Out-Null
    }

    $pythonExe = Join-Path $embedDir "python.exe"
    if (Test-Path $pythonExe) {
        Write-Host "Reusing embedded Python: $pythonExe" -ForegroundColor Green
        return $pythonExe
    }

    Write-Host "Downloading portable Python $version (~25 MB)..." -ForegroundColor Yellow
    Write-Host "URL: $url"
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $embedDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

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

    $getPip = Join-Path $env:TEMP "get-pip.py"
    Write-Host "Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    & $pythonExe $getPip --no-warn-script-location | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed" }

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

function Resolve-GatewayPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallDir
    )

    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $prev = $ErrorActionPreference
            $ErrorActionPreference = 'SilentlyContinue'
            $v = (& py -3 -c "import sys; print(sys.executable)" 2>$null)
            $ErrorActionPreference = $prev
            if ($LASTEXITCODE -eq 0 -and $v) {
                $path = $v.Trim()
                if (Test-Path -LiteralPath $path) { return $path }
            }
        } catch {}
    }

    foreach ($name in @("python3", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $v = Test-GatewayPythonExe -Exe $cmd.Source
        if ($v) { return $v }
    }

    Write-Host "System Python not found - downloading portable Python..." -ForegroundColor Yellow
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
