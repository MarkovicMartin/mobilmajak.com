#!/usr/bin/env bash
# Kontrola před večerním backfillem (spustit na VPS nebo přes SSH).
set -euo pipefail

ACTOR_DIR="${ACTOR_DIR:-/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL}"
cd "$ACTOR_DIR"

FAIL=0
ok() { echo "OK  $*"; }
bad() { echo "FAIL $*"; FAIL=1; }

echo "=== Preflight backfill pre-2024 ==="
echo "Čas: $(date '+%Y-%m-%d %H:%M:%S %Z')"

for f in main.js backfill-pre2024-insert-only.js backfill-pre2024-months.js run-backfill-pre2024-scheduled.sh; do
  [[ -f "$ACTOR_DIR/$f" ]] && ok "soubor $f" || bad "chybí $f"
done

if [[ -f "$ACTOR_DIR/.env.db" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ACTOR_DIR/.env.db"
  set +a
  ok ".env.db načten"
else
  echo "WARN .env.db chybí – použije se heslo z main.js"
fi

if node -e "
const { connectToMySQL } = require('./main.js');
(async () => {
  const c = await connectToMySQL();
  const [ping] = await c.execute('SELECT 1 AS ok');
  const [stat] = await c.execute('SELECT MIN(Vystaveno) mn, COUNT(*) n FROM WEB_PRODEJE_ALL');
  const [pre] = await c.execute(\"SELECT COUNT(*) n FROM WEB_PRODEJE_ALL WHERE Vystaveno < '2024-01-01'\");
  console.log(JSON.stringify({ ping: ping[0], stat: stat[0], pre2024: pre[0] }));
  await c.end();
})().catch(e => { console.error(e.message); process.exit(1); });
" 2>/dev/null | grep -q '"ok":1'; then
  ok "MySQL připojení (connectToMySQL)"
  PRE2024=$(node -e "
const { connectToMySQL } = require('./main.js');
(async () => {
  const c = await connectToMySQL();
  const [pre] = await c.execute(\"SELECT COUNT(*) n FROM WEB_PRODEJE_ALL WHERE Vystaveno < '2024-01-01'\");
  console.log(pre[0].n);
  await c.end();
})();" 2>/dev/null | tail -1)
  if [[ "${PRE2024:-0}" -gt 0 ]]; then
    ok "částečná data před 2024 ($PRE2024 řádků) – hotové měsíce se přeskočí"
  else
    ok "žádná data před 2024 (plný import)"
  fi
else
  bad "MySQL připojení"
fi

LOCK="$ACTOR_DIR/reports/backfill_pre2024.lock"
if [[ -f "$LOCK" ]]; then
  PID=$(cat "$LOCK" 2>/dev/null || true)
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    bad "backfill lock aktivní (PID $PID)"
  else
    rm -f "$LOCK"
    ok "starý lock smazán"
  fi
else
  ok "žádný lock"
fi

if pgrep -f 'node.*backfill-pre2024-months' >/dev/null 2>&1; then
  bad "backfill-pre2024-months.js už běží"
else
  ok "backfill neběží"
fi

echo "=== Výsledek: $([[ $FAIL -eq 0 ]] && echo PASS || echo FAIL) ==="
exit $FAIL
