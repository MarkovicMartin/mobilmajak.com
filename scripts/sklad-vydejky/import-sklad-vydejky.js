#!/usr/bin/env node
/**
 * Import skladových výdejek ze Symplia (subtype ruční / spotřeba / reklamace).
 *
 * Použití:
 *   node import-sklad-vydejky.js --from 2026-06-01 --to 2026-06-30
 *   node import-sklad-vydejky.js   # pouze dnešek
 */
const { Builder, By, until } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const XLSX = require('xlsx');

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

const ALLOWED_SUBTYPES = new Set([20, 25, 202, 252, 204, 254]);
const PODTYP_TO_SUBTYPE = {
  'Vyskladnění z hlavního skladu - ruční': 20,
  'Vyskladnění z komisního skladu - ruční': 25,
  'Vyskladnění z hlavního skladu - reklamace': 202,
  'Vyskladnění z komisního skladu - reklamace': 252,
  'Vyskladnění z hlavního skladu - spotřeba': 204,
  'Vyskladnění z komisního skladu - spotřeba': 254,
};
const SUBTYPE_DUVOD = { 20: 'rucni', 25: 'rucni', 202: 'reklamace', 252: 'reklamace', 204: 'spotreba', 254: 'spotreba' };
const SUBTYPE_SKLAD = { 20: 'hlavni', 25: 'komisni', 202: 'hlavni', 252: 'komisni', 204: 'hlavni', 254: 'komisni' };

function mysqlConfig() {
  return {
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    database: process.env.DB_NAME || 'multi_724223',
    password: process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD || '',
    charset: 'utf8mb4',
  };
}

function parseArgs() {
  const args = process.argv.slice(2);
  let from = null;
  let to = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--from') from = args[++i];
    if (args[i] === '--to') to = args[++i];
  }
  if (!from || !to) {
    const today = new Date().toISOString().slice(0, 10);
    from = from || today;
    to = to || today;
  }
  return { from, to };
}

function parseDokladCislo(nazev) {
  if (!nazev) return null;
  const text = String(nazev).trim();
  const m = text.match(/(S\d+)\s*$/);
  if (m) return m[1];
  if (text.startsWith('S') && /^\S+$/.test(text)) return text;
  return null;
}

function parseCzechDate(value) {
  if (!value) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  const text = String(value).trim();
  const m = text.match(/(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text;
  return null;
}

function parseDecimal(value) {
  if (value === null || value === undefined || value === '') return 0;
  if (typeof value === 'number') return value;
  const text = String(value).replace(/\s/g, '').replace('Kč', '').replace(',', '.');
  const n = parseFloat(text);
  return Number.isFinite(n) ? n : 0;
}

function resolveSubtype(podtyp) {
  if (!podtyp) return null;
  const text = String(podtyp).trim();
  if (PODTYP_TO_SUBTYPE[text]) return PODTYP_TO_SUBTYPE[text];
  const lower = text.toLowerCase();
  const komisni = lower.includes('komisní') || lower.includes('komisni');
  if (lower.includes('ruční') || lower.includes('rucni')) return komisni ? 25 : 20;
  if (lower.includes('spotřeba') || lower.includes('spotreba')) return komisni ? 254 : 204;
  if (lower.includes('reklamace')) return komisni ? 252 : 202;
  return null;
}

function parseDokladRow(row) {
  if (!row || row.length < 5) return null;
  const doklad = parseDokladCislo(row[0]);
  if (!doklad) return null;
  const podtyp = String(row[1] || '').trim();
  const subtype = resolveSubtype(podtyp);
  if (!subtype || !ALLOWED_SUBTYPES.has(subtype)) return null;
  const vystaveno = parseCzechDate(row[4]);
  if (!vystaveno) return null;
  return {
    doklad,
    vystaveno,
    symplio_subtype: subtype,
    duvod_vyskladneni: podtyp,
    sklad_typ: SUBTYPE_SKLAD[subtype],
    duvod_kategorie: SUBTYPE_DUVOD[subtype],
    spravce: row[3] ? String(row[3]).trim() : null,
    vazba: row[2] ? String(row[2]).trim() : null,
    castka_s_dph: parseDecimal(row[7]),
    castka_bez_dph: parseDecimal(row[8] ?? row[7]),
  };
}

async function createDriver(downloadDir) {
  const options = new chrome.Options();
  options.addArguments('--headless=new', '--no-sandbox', '--disable-dev-shm-usage');
  options.setUserPreferences({
    'download.default_directory': downloadDir,
    'download.prompt_for_download': false,
    'download.directory_upgrade': true,
  });
  return new Builder().forBrowser('chrome').setChromeOptions(options).build();
}

async function symplioLogin(driver) {
  await loginSymplio(driver, { store: 'hlavni_sklad' });
}

function eachDayIso(from, to) {
  const days = [];
  const cur = new Date(`${from}T12:00:00`);
  const end = new Date(`${to}T12:00:00`);
  while (cur <= end) {
    days.push(cur.toISOString().slice(0, 10));
    cur.setDate(cur.getDate() + 1);
  }
  return days;
}

function buildUrl(basePath, from, to, subtype = null) {
  let url = `https://www.mobilmajak.cz${basePath}?type%5B0%5D=sklad-vydejka&date_range%5Bfrom%5D=${from}&date_range%5Bto%5D=${to}`;
  if (subtype != null) url += `&subtype=${subtype}`;
  return url;
}

const SUBTYPE_LIST = [20, 25, 202, 252, 204, 254];

async function scrapePolozkyFromPage(driver) {
  const rows = await driver.findElements(By.css('table tbody tr'));
  const out = [];
  for (const row of rows) {
    const cells = await row.findElements(By.css('td'));
    const vals = [];
    for (const c of cells) vals.push((await c.getText()).trim());
    if (vals.length < 7) continue;
    const doklad = vals[3];
    if (!doklad || !doklad.startsWith('S')) continue;
    const pocet = parseInt(String(vals[6]).replace(/\s/g, ''), 10) || 0;
    out.push({
      doklad,
      kod: vals[1] || null,
      nazev: vals[2] || null,
      pocet_kusu: Math.abs(pocet),
      cena_ks_bez_dph: parseDecimal(vals[9]),
      cena_celkem_bez_dph: parseDecimal(vals[10]),
      vystaveno: parseCzechDate(vals[0]),
    });
  }
  return out;
}

async function scrapePolozkyForSubtype(driver, from, to, subtype) {
  await driver.get(buildUrl('/admin/sklady/doklady/polozky', from, to, subtype));
  await sleep(2500);
  let rows = await scrapePolozkyFromPage(driver);
  if (rows.length >= 30) {
    console.warn(`Subtype ${subtype}: ${rows.length} řádků – doplňuji po dnech`);
    const byDay = [];
    for (const day of eachDayIso(from, to)) {
      await driver.get(buildUrl('/admin/sklady/doklady/polozky', day, day, subtype));
      await sleep(2000);
      byDay.push(...await scrapePolozkyFromPage(driver));
    }
    rows = byDay;
  }
  return rows;
}

async function scrapePolozky(driver, from, to) {
  const out = [];
  for (const subtype of SUBTYPE_LIST) {
    const rows = await scrapePolozkyForSubtype(driver, from, to, subtype);
    console.log(`Subtype ${subtype}: ${rows.length} položek`);
    out.push(...rows);
  }
  return out;
}

async function downloadDokladyXlsx(driver, downloadDir, from, to) {
  fs.rmSync(downloadDir, { recursive: true, force: true });
  fs.mkdirSync(downloadDir, { recursive: true });
  await driver.get(buildUrl('/admin/sklady/doklady', from, to));
  await sleep(4000);
  const exportLink = await driver.wait(
    until.elementLocated(By.xpath("//a[contains(@href, '_export=xlsx')]")),
    20000,
  );
  await exportLink.click();
  await sleep(8000);
  const files = fs.readdirSync(downloadDir);
  if (!files.length) throw new Error('XLSX dokladů se nestáhl');
  const wb = XLSX.readFile(path.join(downloadDir, files[0]));
  const sheet = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(sheet, { header: 1, defval: null });
}

async function importToDb(connection, doklady, polozky, allowedDoklady) {
  const dates = [...new Set(doklady.map((d) => d.vystaveno))];
  if (!dates.length) {
    console.log('Žádné doklady k importu');
    return { doklady: 0, polozky: 0 };
  }
  const placeholders = dates.map(() => '?').join(',');
  const [existing] = await connection.execute(
    `SELECT doklad FROM WEB_SKLAD_VYDEJKY WHERE vystaveno IN (${placeholders})`,
    dates,
  );
  if (existing.length) {
    const dokladyPh = existing.map(() => '?').join(',');
    const dokladIds = existing.map((r) => r.doklad);
    await connection.execute(
      `DELETE FROM WEB_SKLAD_VYDEJKA_POLOZKY WHERE doklad IN (${dokladyPh})`,
      dokladIds,
    );
    await connection.execute(
      `DELETE FROM WEB_SKLAD_VYDEJKY WHERE doklad IN (${dokladyPh})`,
      dokladIds,
    );
  }

  for (const d of doklady) {
    await connection.execute(
      `INSERT INTO WEB_SKLAD_VYDEJKY (
        doklad, vystaveno, symplio_subtype, duvod_vyskladneni, sklad_typ, duvod_kategorie,
        spravce, vazba, castka_s_dph, castka_bez_dph
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        d.doklad, d.vystaveno, d.symplio_subtype, d.duvod_vyskladneni, d.sklad_typ, d.duvod_kategorie,
        d.spravce, d.vazba, d.castka_s_dph, d.castka_bez_dph,
      ],
    );
  }

  let polCount = 0;
  for (const p of polozky) {
    if (!allowedDoklady.has(p.doklad)) continue;
    await connection.execute(
      `INSERT INTO WEB_SKLAD_VYDEJKA_POLOZKY (
        doklad, kod, nazev, pocet_kusu, cena_ks_bez_dph, cena_celkem_bez_dph, vystaveno
      ) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        p.doklad, p.kod, p.nazev, p.pocet_kusu, p.cena_ks_bez_dph, p.cena_celkem_bez_dph, p.vystaveno,
      ],
    );
    polCount += 1;
  }
  return { doklady: doklady.length, polozky: polCount };
}

async function main() {
  const { from, to } = parseArgs();
  console.log(`Import skladových výdejek ${from} .. ${to}`);
  const downloadDir = '/tmp/sklad-vydejky-dl';
  const driver = await createDriver(downloadDir);
  let connection;
  try {
    await symplioLogin(driver);
    const xlsxRows = await downloadDokladyXlsx(driver, downloadDir, from, to);
    const doklady = [];
    for (let i = 1; i < xlsxRows.length; i++) {
      const parsed = parseDokladRow(xlsxRows[i]);
      if (parsed) doklady.push(parsed);
    }
    const allowedDoklady = new Set(doklady.map((d) => d.doklad));
    const polozky = await scrapePolozky(driver, from, to);
    console.log(`Nalezeno ${doklady.length} dokladů, ${polozky.length} řádků položek (před filtrem)`);

    connection = await mysql.createConnection(mysqlConfig());
    const result = await importToDb(connection, doklady, polozky, allowedDoklady);
    console.log(`Import OK: ${result.doklady} dokladů, ${result.polozky} položek`);

    const withPolozky = new Set(
      polozky.filter((p) => allowedDoklady.has(p.doklad)).map((p) => p.doklad),
    );
    const missing = doklady.filter((d) => !withPolozky.has(d.doklad));
    if (missing.length) {
      console.warn(
        `Varování: ${missing.length} dokladů bez položek: ${missing.map((d) => d.doklad).join(', ')}`,
      );
      process.exitCode = 2;
    }
  } finally {
    await driver.quit();
    if (connection) await connection.end();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
