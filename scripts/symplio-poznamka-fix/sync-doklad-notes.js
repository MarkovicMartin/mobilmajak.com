#!/usr/bin/env node
/**
 * Stáhne poznámky dokladů ze Symplia (/admin/doklady) a doplní je do WEB_PRODEJE_ALL.
 * Režimy sladěné s Packeta cronem: today | yesterday | audit
 */
const fs = require('fs');
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const { loginSymplio } = require('./symplio-login');
const { fetchDokladNotesMap } = require('./fetch-doklad-notes');
const { applyPoznamkaDokladuMap, connectToMySQL } = require('./apply-poznamka-dokladu');

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatDateLocal(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function dateRangeForMode(mode) {
  const today = new Date();
  if (mode === 'today') {
    const d = formatDateLocal(today);
    return { from: d, to: d };
  }
  if (mode === 'yesterday') {
    const y = new Date(today);
    y.setDate(y.getDate() - 1);
    const d = formatDateLocal(y);
    return { from: d, to: d };
  }
  if (mode === 'audit') {
    const days = parseInt(process.env.PACKETA_AUDIT_DAYS || '7', 10);
    const from = new Date(today);
    from.setDate(from.getDate() - days);
    return { from: formatDateLocal(from), to: formatDateLocal(today) };
  }
  throw new Error(`Neznámý režim: ${mode} (today|yesterday|audit)`);
}

function parseArgs(argv) {
  const out = { mode: 'today', dryRun: false, keepJson: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--mode') out.mode = argv[++i];
    else if (a === '--dry-run') out.dryRun = true;
    else if (a === '--keep-json') out.keepJson = true;
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  const { from, to } = dateRangeForMode(args.mode);
  console.log(`Symplio poznámky dokladů [${args.mode}] ${from}..${to}${args.dryRun ? ' (dry-run)' : ''}`);

  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--headless=new');
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();

  let map = {};
  try {
    await loginSymplio(driver);
    map = await fetchDokladNotesMap(driver, from, to);
  } finally {
    await driver.quit();
  }

  console.log(`Staženo ${Object.keys(map).length} poznámek ze Symplia`);

  const reportsDir = path.join(__dirname, 'reports');
  fs.mkdirSync(reportsDir, { recursive: true });
  const jsonPath = path.join(reportsDir, `poznamka_dokladu_${args.mode}_${from}_${to}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({
    created_at: new Date().toISOString(),
    mode: args.mode,
    period: { from, to },
    count: Object.keys(map).length,
    map,
  }, null, 2));
  console.log(`JSON: ${jsonPath}`);

  const connection = await connectToMySQL();
  try {
    const stats = await applyPoznamkaDokladuMap(connection, map, {
      dateFrom: from,
      dateTo: to,
      dryRun: args.dryRun,
    });
    console.log(`DB UPDATE: dokladů=${stats.dokladyTouched}, řádků=${stats.rowsUpdated}, beze změny=${stats.rowsSkipped}`);
  } finally {
    await connection.end();
  }

  if (!args.keepJson) {
    // ponechat poslední soubor pro diagnostiku – smažeme jen starší stejného režimu
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { dateRangeForMode };
