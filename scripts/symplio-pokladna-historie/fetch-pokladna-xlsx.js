#!/usr/bin/env node
/**
 * Symplio historie pokladny – stáhne XLSX export úhrad a uloží do reports/.
 * Django import: manage.py import_symplio_pokladna --input-dir reports/
 *
 * Cron: run-symplio-pokladna-safe.sh (den 8:30–21 + večer 22:00)
 */
const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

function resolveSymplioDir() {
  const candidates = [
    process.env.SYMPLIO_SCRIPTS_DIR,
    path.join(__dirname, '../symplio-shared'),
    path.join(__dirname, '../symplio-poznamka-fix'),
    '/opt/scripts/symplio-shared',
  ].filter(Boolean);
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, 'symplio-login.js'))) return dir;
  }
  throw new Error(`symplio-login.js nenalezen v: ${candidates.join(', ')}`);
}

const SYMPLIO_DIR = resolveSymplioDir();
const { loginSymplio, sleep } = require(path.join(SYMPLIO_DIR, 'symplio-login'));

const BASE = 'https://www.mobilmajak.cz';
const REPORTS_DIR = path.join(__dirname, 'reports');
const POKLADNY_FILE = path.join(__dirname, 'pokladny.json');
const DAYS_BACK = parseInt(process.env.SYMPLIO_POKLADNA_DAYS || '7', 10);

function loadPokladny() {
  if (!fs.existsSync(POKLADNY_FILE)) {
    throw new Error(`Chybí konfigurace: ${POKLADNY_FILE}`);
  }
  const data = JSON.parse(fs.readFileSync(POKLADNY_FILE, 'utf8'));
  return (data.pokladny || []).filter((p) => p.enabled);
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function dateRange() {
  const fromEnv = process.env.SYMPLIO_DATE_FROM;
  const toEnv = process.env.SYMPLIO_DATE_TO;
  if (fromEnv && toEnv) {
    return { from: fromEnv.slice(0, 10), to: toEnv.slice(0, 10) };
  }
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - Math.max(1, DAYS_BACK) + 1);
  return { from: isoDate(from), to: isoDate(to) };
}

async function loginForPokladna(driver, storeButton) {
  await loginSymplio(driver, { store: storeButton || null });
}

function buildExportUrl(adminSlug, from, to) {
  const q = new URLSearchParams({
    'date_range[from]': from,
    'date_range[to]': to,
    _export: 'xlsx',
  });
  return `${BASE}/admin/pokladny/${adminSlug}/historie-hotovosti?${q.toString()}`;
}

function chromeDownloadDir() {
  const dir = process.env.SYMPLIO_POKLADNA_DOWNLOAD_DIR || path.join(__dirname, 'downloads');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function clearDownloadDir(dir) {
  for (const f of fs.readdirSync(dir)) {
    if (f.endsWith('.xlsx') || f.endsWith('.crdownload')) {
      fs.unlinkSync(path.join(dir, f));
    }
  }
}

async function waitForDownload(dir, timeoutMs = 120000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.xlsx'));
    if (files.length) {
      const full = path.join(dir, files[0]);
      const size1 = fs.statSync(full).size;
      await sleep(1500);
      const size2 = fs.statSync(full).size;
      if (size1 > 0 && size1 === size2) return full;
    }
    await sleep(500);
  }
  throw new Error(`Timeout čekání na XLSX download v ${dir}`);
}

async function downloadXlsxViaBrowser(driver, url, outPath) {
  const dlDir = chromeDownloadDir();
  clearDownloadDir(dlDir);
  await driver.get(url);
  await sleep(2000);
  const downloaded = await waitForDownload(dlDir);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.copyFileSync(downloaded, outPath);
  clearDownloadDir(dlDir);

  const buf = fs.readFileSync(outPath);
  if (buf[0] !== 0x50 || buf[1] !== 0x4b) {
    throw new Error(`Stažený soubor není XLSX: ${outPath}`);
  }
  const rows = XLSX.utils.sheet_to_json(XLSX.read(buf).Sheets.Sheet1, { header: 1 });
  const headers = (rows[0] || []).map((h) => String(h || '').trim());
  if (!headers.includes('Datum') || !headers.includes('Částka')) {
    throw new Error(`XLSX nemá očekávané sloupce: ${headers.join(', ')}`);
  }
  console.log('Staženo', outPath, buf.length, 'B, řádků', Math.max(0, rows.length - 1));
  return rows.length - 1;
}

function writeMeta(xlsxPath, pokladna, from, to) {
  const metaPath = xlsxPath.replace(/\.xlsx$/i, '.meta.json');
  fs.writeFileSync(
    metaPath,
    JSON.stringify(
      {
        prodejna_id: pokladna.prodejna_id,
        key: pokladna.key,
        label: pokladna.label,
        date_from: from,
        date_to: to,
        fetched_at: new Date().toISOString(),
      },
      null,
      2,
    ),
    'utf8',
  );
}

async function main() {
  const pokladny = loadPokladny();
  if (!pokladny.length) {
    console.log('Žádná enabled pokladna v pokladny.json – nic ke stažení.');
    return;
  }

  const { from, to } = dateRange();
  console.log(`Symplio pokladna export ${from} – ${to}, pokladen: ${pokladny.length}`);

  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--headless=new');
  const dlDir = chromeDownloadDir();
  options.setUserPreferences({
    'download.default_directory': dlDir,
    'download.prompt_for_download': false,
    'safebrowsing.enabled': false,
  });
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();

  try {
    for (const pokladna of pokladny) {
      console.log(`\n→ ${pokladna.label} (${pokladna.admin_slug}, prodejna_id=${pokladna.prodejna_id})`);
      const out = path.join(REPORTS_DIR, `uhrady_${pokladna.key}_${from}_${to}.xlsx`);
      if (fs.existsSync(out) && fs.statSync(out).size > 1000) {
        console.log('Přeskočeno – soubor už existuje:', out);
        if (!fs.existsSync(out.replace(/\.xlsx$/i, '.meta.json'))) {
          writeMeta(out, pokladna, from, to);
        }
        continue;
      }
      await loginForPokladna(driver, pokladna.store_button);
      const url = buildExportUrl(pokladna.admin_slug, from, to);
      await downloadXlsxViaBrowser(driver, url, out);
      writeMeta(out, pokladna, from, to);
    }
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
