#!/usr/bin/env node
/**
 * Symplio historie pokladny – stáhne XLSX export úhrad a uloží do reports/.
 * Django import: manage.py import_symplio_pokladna --input-dir reports/inbox/
 *
 * Cron: run-symplio-pokladna-safe.sh (den 8:30–21 + večer 22:00)
 */
const fs = require('fs');
const path = require('path');
const axios = require('axios');
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
const INBOX_DIR = path.join(REPORTS_DIR, 'inbox');
const POKLADNY_FILE = path.join(__dirname, 'pokladny.json');
const DAYS_BACK = parseInt(process.env.SYMPLIO_POKLADNA_DAYS || '7', 10);

function loadPokladny() {
  if (!fs.existsSync(POKLADNY_FILE)) {
    throw new Error(`Chybí konfigurace: ${POKLADNY_FILE}`);
  }
  const data = JSON.parse(fs.readFileSync(POKLADNY_FILE, 'utf8'));
  const only = (process.env.SYMPLIO_POKLADNA_ONLY || '').split(',').map((s) => s.trim()).filter(Boolean);
  return (data.pokladny || []).filter((p) => p.enabled && (!only.length || only.includes(p.key)));
}

function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function resetInbox() {
  fs.rmSync(INBOX_DIR, { recursive: true, force: true });
  fs.mkdirSync(INBOX_DIR, { recursive: true });
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

function assertXlsx(buf, outPath) {
  if (!buf || buf.length < 4 || buf[0] !== 0x50 || buf[1] !== 0x4b) {
    const preview = Buffer.from(buf || []).slice(0, 100).toString('utf8').replace(/\s+/g, ' ').slice(0, 100);
    throw new Error(`Stažený soubor není XLSX (${buf ? buf.length : 0} B): ${preview}`);
  }
  const rows = XLSX.utils.sheet_to_json(XLSX.read(buf).Sheets.Sheet1, { header: 1 });
  const headers = (rows[0] || []).map((h) => String(h || '').trim());
  if (!headers.includes('Datum') || !headers.includes('Částka')) {
    throw new Error(`XLSX nemá očekávané sloupce: ${headers.join(', ')}`);
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  const count = Math.max(0, rows.length - 1);
  console.log('Staženo', outPath, buf.length, 'B, řádků', count);
  return count;
}

async function cookieHeader(driver) {
  const cookies = await driver.manage().getCookies();
  return cookies.map((c) => `${c.name}=${c.value}`).join('; ');
}

async function downloadXlsxViaHttp(driver, url, outPath) {
  const response = await axios.get(url, {
    responseType: 'arraybuffer',
    timeout: 90000,
    maxContentLength: 40 * 1024 * 1024,
    maxBodyLength: 40 * 1024 * 1024,
    headers: {
      Cookie: await cookieHeader(driver),
      Accept: '*/*',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    },
    validateStatus: () => true,
  });
  const buf = Buffer.from(response.data || []);
  if (response.status !== 200) {
    const html = buf.toString('utf8');
    const title = (html.match(/<title>([^<]*)/i) || [])[1] || '';
    throw new Error(`Export HTTP ${response.status} (${buf.length} B) ${title.trim()}`);
  }
  return assertXlsx(buf, outPath);
}

async function waitForDownload(dir, timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.xlsx'));
    if (files.length) {
      const full = path.join(dir, files[0]);
      const size1 = fs.statSync(full).size;
      await sleep(800);
      const size2 = fs.statSync(full).size;
      if (size1 > 0 && size1 === size2) return full;
    }
    await sleep(400);
  }
  throw new Error(`Timeout čekání na XLSX download v ${dir}`);
}

async function downloadXlsxViaBrowser(driver, url, outPath) {
  const dlDir = chromeDownloadDir();
  clearDownloadDir(dlDir);
  await driver.get(url);
  await sleep(1500);
  const downloaded = await waitForDownload(dlDir);
  const buf = fs.readFileSync(downloaded);
  clearDownloadDir(dlDir);
  return assertXlsx(buf, outPath);
}

async function downloadXlsx(driver, url, outPath) {
  try {
    return await downloadXlsxViaHttp(driver, url, outPath);
  } catch (err) {
    console.log('HTTP export selhal, zkouším stažení v prohlížeči:', err && err.message ? err.message : err);
    return downloadXlsxViaBrowser(driver, url, outPath);
  }
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
  resetInbox();
  console.log(`Symplio pokladna export ${from} – ${to} (DAYS=${DAYS_BACK}), pokladen: ${pokladny.length}`);

  const options = new chrome.Options();
  const chromeArgs = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
    '--window-size=1920,1080',
    '--lang=cs-CZ',
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Safari/537.36',
  ];
  if (process.env.SYMPLIO_POKLADNA_HEADLESS === '1') {
    chromeArgs.push('--headless=new');
  }
  options.addArguments(...chromeArgs);
  try {
    options.excludeSwitches('enable-automation');
  } catch (_) { /* starší selenium */ }
  const dlDir = chromeDownloadDir();
  options.setUserPreferences({
    'download.default_directory': dlDir,
    'download.prompt_for_download': false,
    'safebrowsing.enabled': false,
  });
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await driver.pinScript("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})");
  } catch (err) {
    console.log('pinScript:', err && err.message ? err.message : err);
  }

  const failed = [];
  try {
    for (const pokladna of pokladny) {
      console.log(`\n→ ${pokladna.label} (${pokladna.admin_slug}, prodejna_id=${pokladna.prodejna_id})`);
      const out = path.join(INBOX_DIR, `uhrady_${pokladna.key}.xlsx`);
      try {
        await loginForPokladna(driver, pokladna.store_button);
        const url = buildExportUrl(pokladna.admin_slug, from, to);
        await downloadXlsx(driver, url, out);
        writeMeta(out, pokladna, from, to);
      } catch (err) {
        failed.push(pokladna);
        console.error(`Selhalo ${pokladna.label}:`, err && err.message ? err.message : err);
      }
    }
    for (const pokladna of failed.splice(0)) {
      console.log(`\n→ znovu ${pokladna.label}`);
      const out = path.join(INBOX_DIR, `uhrady_${pokladna.key}.xlsx`);
      try {
        await loginForPokladna(driver, pokladna.store_button);
        const url = buildExportUrl(pokladna.admin_slug, from, to);
        await downloadXlsx(driver, url, out);
        writeMeta(out, pokladna, from, to);
      } catch (err) {
        failed.push(pokladna);
        console.error(`Znovu selhalo ${pokladna.label}:`, err && err.message ? err.message : err);
      }
    }
  } finally {
    await driver.quit();
  }
  if (failed.length) {
    console.error(`Selhalo pokladen: ${failed.length}/${pokladny.length}`);
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
