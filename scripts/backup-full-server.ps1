# Kompletní záloha VPS + lokální repo → ../mobilmajak-backups/
# Vyžaduje bash (Mac/Linux). Na Windows použijte WSL nebo Git Bash.
param(
    [switch]$WithNodeModules
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$sh = Join-Path $RepoRoot "scripts/backup-full-server.sh"

if (-not (Test-Path $sh)) { throw "Chybí $sh" }

$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
    throw "Není nainstalován bash (na Macu: příkaz bash je v PATH)."
}

$args = @()
if ($WithNodeModules) { $args += "--with-node-modules" }

& $bash.Source $sh @args
