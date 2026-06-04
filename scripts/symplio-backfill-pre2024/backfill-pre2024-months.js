#!/usr/bin/env node
/**
 * Backfill 2017-10 .. 2023-12 po měsících – pouze insert-only skript.
 * Usage: node backfill-pre2024-months.js
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const START = { y: 2017, m: 10 };
const END = { y: 2023, m: 12 };
const SCRIPT = path.join(__dirname, 'backfill-pre2024-insert-only.js');
const LOG = path.join(__dirname, 'reports', 'backfill_pre2024_months.log');

function parseYm(s) {
  const [y, m] = s.split('-').map(Number);
  return { y, m };
}

function nextYm({ y, m }) {
  if (m === 12) return { y: y + 1, m: 1 };
  return { y, m: m + 1 };
}

function ymStr({ y, m }) {
  return `${y}-${String(m).padStart(2, '0')}`;
}

function lastDay(y, m) {
  return new Date(y, m, 0).getDate();
}

function lte(a, b) {
  return a.y < b.y || (a.y === b.y && a.m <= b.m);
}

const start = process.argv[2] ? parseYm(process.argv[2]) : START;
const end = process.argv[3] ? parseYm(process.argv[3]) : END;
const CONTINUE_ON_ERROR = process.argv.includes('--continue') || process.env.BACKFILL_CONTINUE === '1';
const SLEEP_SEC = parseInt(process.env.BACKFILL_SLEEP_SEC || '60', 10);

fs.mkdirSync(path.dirname(LOG), { recursive: true });

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG, line);
  console.log(msg);
}

let cur = start;
while (lte(cur, end)) {
  const from = `${cur.y}-${String(cur.m).padStart(2, '0')}-01`;
  const to = `${cur.y}-${String(cur.m).padStart(2, '0')}-${String(lastDay(cur.y, cur.m)).padStart(2, '0')}`;
  log(`>>> MONTH ${from} .. ${to}`);
  const r = spawnSync(process.execPath, [SCRIPT, '--from', from, '--to', to, '--download'], {
    cwd: __dirname,
    env: process.env,
    stdio: 'inherit',
  });
  if (r.status !== 0) {
    log(`FAILED ${from} ${to} exit=${r.status}`);
    if (!CONTINUE_ON_ERROR) process.exit(r.status || 1);
  } else {
    log(`OK ${from} ${to}`);
  }
  cur = nextYm(cur);
  if (lte(cur, end)) {
    log(`Sleep ${SLEEP_SEC}s...`);
    spawnSync('sleep', [String(SLEEP_SEC)]);
  }
}
log('All months done.');
if (CONTINUE_ON_ERROR) {
  const failed = fs.readFileSync(LOG, 'utf8').split('\n').filter((l) => l.includes('FAILED')).length;
  if (failed > 0) process.exit(1);
}
