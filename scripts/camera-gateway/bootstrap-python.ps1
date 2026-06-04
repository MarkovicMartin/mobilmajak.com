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

function Resolve-GatewayPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallDir
    )

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $v = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) { return $v.Trim() }
    }
    foreach ($name in @("python3", "python")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            $v = & $name -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) { return $v.Trim() }
        }
    }

    return Install-EmbeddedPython -TargetDir $InstallDir
}
