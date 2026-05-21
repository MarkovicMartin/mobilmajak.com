# MOBILMAJAK: auto-povolit čtení/testy; ptát se na síť; git commit/push jen po žádosti v chatu.
$ErrorActionPreference = 'Stop'

function Emit-Permission {
    param(
        [string]$Permission,
        [string]$UserMessage = '',
        [string]$AgentMessage = ''
    )
    $out = [ordered]@{ permission = $Permission }
    if ($UserMessage) { $out.user_message = $UserMessage }
    if ($AgentMessage) { $out.agent_message = $AgentMessage }
    $out | ConvertTo-Json -Compress
}

function Test-UserRequestedGitAction {
    param([string]$TranscriptPath)
    if (-not $TranscriptPath -or -not (Test-Path -LiteralPath $TranscriptPath)) {
        return $false
    }
    try {
        $tail = Get-Content -LiteralPath $TranscriptPath -Tail 120 -ErrorAction SilentlyContinue
        if (-not $tail) { return $false }
        $text = ($tail -join "`n").ToLowerInvariant()
        $patterns = @(
            'commitni', 'ud[eě]lej commit', 'vytvo[rř] commit', 'git commit',
            'pushni', 'git push', 'nahraj', 'push to', 'create a git commit',
            'create commit', 'vytvo[rř] pr', 'create pr', 'pull request',
            'gh pr create', 'merge pr', 'commit changes', 'zcommituj'
        )
        foreach ($p in $patterns) {
            if ($text -match $p) { return $true }
        }
    }
    catch { }
    return $false
}

$raw = [Console]::In.ReadToEnd()
if (-not $raw) {
    Emit-Permission 'allow'
    exit 0
}

try {
    $payload = $raw | ConvertFrom-Json
}
catch {
    if ($raw -match 'git\s+(commit|push)|\b(ssh|curl|deploy)\b') {
        Emit-Permission 'ask' 'Příkaz vyžaduje potvrzení (nelze automaticky ověřit).' ''
        exit 0
    }
    Emit-Permission 'allow'
    exit 0
}

$command = [string]$payload.command
$transcript = [string]$payload.transcript_path

if ([string]::IsNullOrWhiteSpace($command)) {
    Emit-Permission 'allow'
    exit 0
}

$cmd = $command.Trim()

# Auto-povolit: read-only git, testy, lint, kontroly, lokální testovací relace MOBILMAJAK
$autoAllow = @(
    '^(git\s+(status|diff|log|show|branch|rev-parse|remote\s+-v))',
    '^(npm\s+(test|run\s+test)|pnpm\s+test|yarn\s+test)',
    '^(npm\s+run\s+(build|serve:build)\b)',
    'run-local\.(ps1|cmd)',
    'scripts\\run-local',
    '^(python\s+-m\s+)?pytest\b',
    '^(python\s+manage\.py\s+check)',
    '^(ruff\s+check|flake8|eslint|tsc\s+--noEmit)',
    '^(cargo\s+test|go\s+test\b)',
    'manage\.py\s+\w+\s+--dry-run'
)
foreach ($re in $autoAllow) {
    if ($cmd -match $re) {
        Emit-Permission 'allow'
        exit 0
    }
}

# Síť, deploy, SSH – vždy ptát
$networkOrDeploy = @(
    '\bcurl\b', '\bwget\b', 'Invoke-WebRequest', 'Invoke-RestMethod',
    '\bssh\b', '\bscp\b', '\brsync\b', 'deploy\.sh', 'deploy-production',
    '194\.182\.', 'webglobe', 'gunicorn\s+restart'
)
foreach ($re in $networkOrDeploy) {
    if ($cmd -match $re) {
        Emit-Permission 'ask' `
            'Příkaz může odeslat data online nebo měnit vzdálený server – potvrďte prosím.' `
            'Hook vyžaduje potvrzení: síťový/deploy/SSH příkaz.'
        exit 0
    }
}

# Git commit / push / gh – povolit jen po explicitní žádosti v transkriptu
$gitSensitive = '^(git\s+(commit|push|rebase|reset|checkout\s+-f)|gh\s+(pr|repo\s+sync|api))'
if ($cmd -match $gitSensitive) {
    if (Test-UserRequestedGitAction -TranscriptPath $transcript) {
        Emit-Permission 'allow'
        exit 0
    }
    Emit-Permission 'ask' `
        'Git/GitHub příkaz vyžaduje potvrzení. Pokud jste o commit/push/PR žádal(a) v chatu, schvalte.' `
        'Spusť git commit/push/gh jen pokud uživatel v tomto chatu výslovně požádal.'
    exit 0
}

# Výchozí: nechat IDE/sandbox (často už auto-povoleno)
Emit-Permission 'allow'
exit 0
