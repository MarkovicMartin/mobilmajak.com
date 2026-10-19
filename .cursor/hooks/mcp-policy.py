#!/usr/bin/env python3
"""MCP: výchozí potvrzení; read-only nástroje bez ptaní."""
import json
import re
import sys


def emit(permission, user_message="", agent_message=""):
    out = {"permission": permission}
    if user_message:
        out["user_message"] = user_message
    if agent_message:
        out["agent_message"] = agent_message
    sys.stdout.write(json.dumps(out, separators=(",", ":")))
    sys.stdout.write("\n")


raw = sys.stdin.read()
if not raw.strip():
    emit("ask", "MCP volání vyžaduje potvrzení.")
    sys.exit(0)

try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    emit("ask", "MCP volání vyžaduje potvrzení.", "Nečitelný MCP payload.")
    sys.exit(0)

tool = str(payload.get("tool_name") or "")
url = str(payload.get("url") or "")

for name in ("list", "get", "read", "search", "status", "help"):
    if re.search(rf"(?i){name}$", tool):
        emit("allow")
        sys.exit(0)

if url and not re.match(r"^(https?://)?(localhost|127\.0\.0\.1)", url):
    emit(
        "ask",
        "MCP může odeslat data na externí službu – potvrďte prosím.",
        "Externí MCP/WebFetch vyžaduje potvrzení uživatele.",
    )
    sys.exit(0)

emit("ask", "MCP nástroj vyžaduje potvrzení.", "Neznámé MCP – schvalte v UI.")
