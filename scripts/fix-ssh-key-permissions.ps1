# Nastaví práva pro OpenSSH na Windows (jen váš účet)
$key = Join-Path $PSScriptRoot ".." ".ssh" "webmajak_vps" "napojeno_ed25519"
$key = (Resolve-Path $key -ErrorAction Stop).Path
icacls $key /inheritance:r /grant:r "${env:USERNAME}:(F)" | Out-Null
Write-Host "OK: $key"
Write-Host "Test: ssh -i `"$key`" root@194.182.87.138"
