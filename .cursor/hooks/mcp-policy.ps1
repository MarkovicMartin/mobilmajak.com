# MCP: výchozí potvrzení; read-only nástroje bez ptaní.
$ErrorActionPreference = 'Stop'

function Emit-Permission {
    param([string]$Permission, [string]$UserMessage = '', [string]$AgentMessage = '')
    $out = [ordered]@{ permission = $Permission }
    if ($UserMessage) { $out.user_message = $UserMessage }
    if ($AgentMessage) { $out.agent_message = $AgentMessage }
    $out | ConvertTo-Json -Compress
}

$raw = [Console]::In.ReadToEnd()
if (-not $raw) {
    Emit-Permission 'ask' 'MCP volání vyžaduje potvrzení.' ''
    exit 0
}

$payload = $raw | ConvertFrom-Json
$tool = [string]$payload.tool_name
$url = [string]$payload.url

# Lokální / read-only MCP (upravte podle vašich serverů)
$safeTools = @('list', 'get', 'read', 'search', 'status', 'help')
foreach ($s in $safeTools) {
    if ($tool -match "(?i)$s`$") {
        Emit-Permission 'allow'
        exit 0
    }
}

# Web / externí URL
if ($url -and $url -notmatch '^(https?://)?(localhost|127\.0\.0\.1)') {
    Emit-Permission 'ask' `
        'MCP může odeslat data na externí službu – potvrďte prosím.' `
        'Externí MCP/WebFetch vyžaduje potvrzení uživatele.'
    exit 0
}

Emit-Permission 'ask' 'MCP nástroj vyžaduje potvrzení.' 'Neznámé MCP – schvalte v UI.'
exit 0
