#!/usr/bin/env node
/**
 * Symplio historie pokladny – stáhne XLSX export úhrad a uloží do reports/.
 * Django import: manage.py import_symplio_pokladna --input-dir reports/
 *
 * Cron: run-symplio-pokladna-safe.sh (22:00)
 */
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const { loginSymplio, sleep } = require('../symplio-poznamka-fix/symplio-login');

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
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - Math.max(1, DAYS_BACK) + 1);
  return { from: isoDate(from), to: isoDate(to) };
}

async function selectStore(driver, storeButton) {
  if (!storeButton) return;
  const xpath = `//a[contains(@class, 'btn-primary') and contains(., '${storeButton}')]`;
  try {
    await driver.findElement(By.xpath(xpath)).click();
    await sleep(2000);
  } catch (err) {
    console.warn(`Store button "${storeButton}" nenalezen, pokračuji:`, err.message);
  }
}

async function loginForPokladna(driver, storeButton) {
  await loginSymplio(driver, { selectGlobus: false });
  await selectStore(driver, storeButton);
}

function buildExportUrl(adminSlug, from, to) {
  const q = new URLSearchParams({
    'date_range[from]': from,
    'date_range[to]': to,
    _export: 'xlsx',
  });
  return `${BASE}/admin/pokladny/${adminSlug}/historie?${q.toString()}`;
}

async function downloadXlsx(driver, url, outPath, attempts = 3) {
  const cookies = await driver.manage().getCookies();
  const cookieString = cookies.map((c) => `${c.name}=${c.value}`).join('; ');

  for (let attempt = 1; attempt <= attempts; attempt++) {
    const r = await axios.get(url, {
      responseType: 'arraybuffer',
      headers: { Cookie: cookieString },
      timeout: 120000,
      validateStatus: () => true,
    });
    const buf = Buffer.from(r.data);
    if (buf.slice(0, 2).toString('utf8') === 'PK') {
      fs.mkdirSync(path.dirname(outPath), { recursive: true });
      fs.writeFileSync(outPath, buf);
      const rows = XLSX.utils.sheet_to_json(XLSX.read(buf).Sheets.Sheet1, { header: 1 });
      const headers = (rows[0] || []).map((h) => String(h || '').trim());
      if (headers.includes('Datum') && headers.includes('Částka')) {
        console.log('Staženo', outPath, buf.length, 'řádků', Math.max(0, rows.length - 1));
        return rows.length - 1;
      }
      console.warn('XLSX nemá očekávané hlavičky:', headers);
    } else {
      console.warn(`Pokus ${attempt}: odpověď není XLSX (${r.status}, ${buf.length} B)`);
    }
    await sleep(10000);
    await driver.get(url.replace('&_export=xlsx', '').replace('?_export=xlsx', ''));
    await sleep(5000);
  }
  throw new Error(`XLSX export selhal: ${url}`);
}

function writeMeta(xlsxPath, pokladna) {
  const metaPath = xlsxPath.replace(/\.xlsx$/i, '.meta.json');
  fs.writeFileSync(
    metaPath,
    JSON.stringify(
      {
        prodejna_id: pokladna.prodejna_id,
        key: pokladna.key,
        label: pokladna.label,
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
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();

  try {
    for (const pokladna of pokladny) {
      console.log(`\n→ ${pokladna.label} (${pokladna.admin_slug}, prodejna_id=${pokladna.prodejna_id})`);
      await loginForPokladna(driver, pokladna.store_button);
      const url = buildExportUrl(pokladna.admin_slug, from, to);
      const out = path.join(REPORTS_DIR, `uhrady_${pokladna.key}_${from}_${to}.xlsx`);
      await downloadXlsx(driver, url, out);
      writeMeta(out, pokladna);
    }
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
