#!/usr/bin/env node
/**
 * Dry-run compare: Symplio XLSX vs WEB_PRODEJE_ALL (bez INSERT/UPDATE/DELETE).
 *   node compare.js --from 2026-04-01 --to 2026-04-30 --download
 *   node compare.js --file /path/polozky.xlsx --from 2026-04-21 --to 2026-04-21
 */
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const mysql = require('mysql2/promise');
const { Builder, By, until } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function convertExcelDate(excelDate) {
  if (!excelDate) return null;
  if (typeof excelDate === 'string') {
    const clean = excelDate.replace(/\s+/g, '');
    const m = clean.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
    if (m) return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
    if (/^\d{4}-\d{2}-\d{2}$/.test(excelDate)) return excelDate;
  }
  if (typeof excelDate === 'number') {
    const excelEpoch = new Date(1900, 0, 1);
    return new Date(excelEpoch.getTime() + (excelDate - 2) * 86400000).toISOString().split('T')[0];
  }
  if (excelDate instanceof Date) return excelDate.toISOString().split('T')[0];
  return null;
}

function parseArgs(argv) {
  const out = { download: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--download') out.download = true;
    else if (a === '--from') out.from = argv[++i];
    else if (a === '--to') out.to = argv[++i];
    else if (a === '--file') out.file = argv[++i];
    else if (a === '--out') out.out = argv[++i];
  }
  if (!out.from || !out.to) throw new Error('Chybí --from a --to (YYYY-MM-DD)');
  return out;
}

function toCzDate(iso) {
  const [y, m, d] = iso.split('-');
  const dt = new Date(parseInt(y, 10), parseInt(m, 10) - 1, parseInt(d, 10));
  return dt.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function toExportUrlDate(czDateStr) {
  return czDateStr.split('.').reverse().join('-').replace(/\s+/g, '');
}

async function handleWafChallenge(driver) {
  try {
    const pageText = await driver.getPageSource();
    if (pageText.includes('WAF') || pageText.includes('Cloudflare') || pageText.includes('DDoS')) {
      console.log('Detekována WAF výzva, čekám...');
      await sleep(5000);
    }
  } catch (e) {
    console.log('WAF check:', e.message);
  }
}

function dupKey(date, cas, kod, doklad) {
  return `${date}|${cas || ''}|${kod || ''}|${doklad || ''}`;
}

async function downloadFileWithAxios(url, cookies, outputPath) {
  try {
    const response = await axios({
      method: 'GET',
      url,
      responseType: 'arraybuffer',
      headers: {
        Cookie: cookies,
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
      },
    });
    fs.writeFileSync(outputPath, response.data);
    return true;
  } catch (error) {
    console.error('Chyba při HTTP stahování:', error.message);
    return false;
  }
}

async function downloadXlsx(fromIso, toIso, outputPath) {
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu');
  options.addArguments('--disable-blink-features=AutomationControlled');
  options.addArguments('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36');
  if (process.env.HEADLESS !== '0') options.addArguments('--headless=new');
  const downloadDir = '/tmp/compare_downloads';
  fs.mkdirSync(downloadDir, { recursive: true });
  options.setUserPreferences({
    'download.default_directory': downloadDir,
    'download.prompt_for_download': false,
    'download.directory_upgrade': true,
    'safebrowsing.enabled': true,
  });
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    const dateFromStr = toCzDate(fromIso);
    const dateToStr = toCzDate(toIso);
    console.log(`Stahuji Symplio export ${dateFromStr} – ${dateToStr}`);
    await driver.get('https://www.mobilmajak.cz/admin');
    await sleep(2000);
    await handleWafChallenge(driver);
    await driver.wait(until.elementLocated(By.name('_username')), 30000);
    await driver.findElement(By.name('_username')).sendKeys(process.env.SYMPLIO_USER || 'APIFY');
    await driver.findElement(By.name('_password')).sendKeys(process.env.SYMPLIO_PASS || 'Apify123!');
    await driver.findElement(By.xpath("//button[@type='submit' and contains(., 'Přihlásit')]")).click();
    await sleep(3000);
    await handleWafChallenge(driver);
    await driver.wait(until.elementLocated(By.xpath("//a[contains(@class, 'btn-primary') and contains(., 'Globus')]")), 30000);
    await driver.findElement(By.xpath("//a[contains(@class, 'btn-primary') and contains(., 'Globus')]")).click();
    await sleep(2000);
    await driver.get('https://www.mobilmajak.cz/admin/doklady/polozky');
    await sleep(4000);
    await handleWafChallenge(driver);

    const exportUrl =
      `https://www.mobilmajak.cz/admin/doklady/polozky?type%5B0%5D=faktura-faktura&type%5B1%5D=faktura-storno&type%5B2%5D=faktura-dobropis&type%5B3%5D=uctenka-uctenka&type%5B4%5D=uctenka-storno&type%5B5%5D=uctenka-dobropis&type%5B6%5D=buctenka-buctenka&type%5B7%5D=buctenka-storno&type%5B8%5D=buctenka-dobropis&date_range%5Bfrom%5D=${toExportUrlDate(dateFromStr)}&date_range%5Bto%5D=${toExportUrlDate(dateToStr)}&list-type=invoice-list&_export=xlsx`;
    console.log('Export URL (HTTP):', exportUrl);

    const cookies = await driver.manage().getCookies();
    const cookieString = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
    const tmpPath = path.join(downloadDir, 'polozky-export.xlsx');

    const maxAttempts = 3;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      if (attempt > 1) {
        console.log(`Opakování stažení (${attempt}/${maxAttempts})...`);
        await driver.get('https://www.mobilmajak.cz/admin/doklady/polozky');
        await sleep(5000);
        await handleWafChallenge(driver);
      }
      const ok = await downloadFileWithAxios(exportUrl, cookieString, tmpPath);
      if (!ok) {
        if (attempt === maxAttempts) throw new Error('HTTP stažení XLSX selhalo');
        await sleep(15000);
        continue;
      }
      const buf = fs.readFileSync(tmpPath);
      if (buf.slice(0, 2).toString('utf8') === 'PK') {
        fs.mkdirSync(path.dirname(outputPath), { recursive: true });
        fs.copyFileSync(tmpPath, outputPath);
        console.log(`Staženo: ${outputPath} (${buf.length} B)`);
        return outputPath;
      }
      console.warn(`Pokus ${attempt}: stažený soubor není XLSX (${buf.length} B, začátek: ${buf.slice(0, 20).toString('utf8').replace(/\s+/g, ' ')})`);
      if (attempt < maxAttempts) await sleep(20000);
    }
    throw new Error('Stažený soubor není platné XLSX po opakování');
  } finally {
    await driver.quit();
  }
}

function parseXlsx(filePath) {
  const wb = XLSX.readFile(filePath);
  const sheet = wb.Sheets[wb.SheetNames[0]];
  const json = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: null });
  const headers = json[0] || [];
  const C = {};
  headers.forEach((h, i) => {
    if (h) C[h.toString().trim()] = i;
  });
  const rows = [];
  for (let i = 1; i < json.length; i++) {
    const row = json[i];
    if (!row || row.length === 0) continue;
    const g = (name) => (C[name] !== undefined ? row[C[name]] : null);
    const date = convertExcelDate(g('Vystaveno'));
    if (!date) continue;
    rows.push({
      date,
      cas: (g('Vystaveno (čas)') || '').toString(),
      kod: (g('Kód') || '').toString(),
      doklad: (g('Doklad') || '').toString(),
      nazev: (g('Název') || '').toString(),
      pocet: parseInt(g('Počet kusů'), 10) || 0,
      cena: parseFloat(g('Cena ks vč. DPH')) || 0,
    });
  }
  return { headers: headers.map((h) => (h || '').toString()), rows };
}

function simulateActorSkip(symplioRows) {
  const existingSet = new Set();
  let wouldInsert = 0;
  let wouldSkip = 0;
  const skippedSamples = [];
  for (const r of symplioRows) {
    const key = dupKey(r.date, r.cas, r.kod, r.doklad);
    if (existingSet.has(key)) {
      wouldSkip++;
      if (skippedSamples.length < 80) skippedSamples.push({ ...r, dupKey: key });
    } else {
      existingSet.add(key);
      wouldInsert++;
    }
  }
  return { wouldInsert, wouldSkip, skippedSamples };
}

const DB_TABLE = process.env.PRODEJE_TABLE || 'WEB_PRODEJE_ALL';

async function loadDbRows(connection, fromIso, toIso) {
  const [rows] = await connection.execute(
    `SELECT id, Vystaveno, cas_prodeje, Kod, Doklad, Pocet_kusu, Cena_ks_vcl_DPH, ID_PRODEJCE
     FROM ${DB_TABLE} WHERE Vystaveno >= ? AND Vystaveno <= ?`,
    [fromIso, toIso],
  );
  return rows.map((r) => {
    const date = r.Vystaveno
      ? `${r.Vystaveno.getFullYear()}-${String(r.Vystaveno.getMonth() + 1).padStart(2, '0')}-${String(r.Vystaveno.getDate()).padStart(2, '0')}`
      : '';
    const cas = r.cas_prodeje ? r.cas_prodeje.toString() : '';
    return {
      id: r.id,
      date,
      cas,
      kod: r.Kod || '',
      doklad: r.Doklad || '',
      pocet: r.Pocet_kusu || 0,
      cena: parseFloat(r.Cena_ks_vcl_DPH) || 0,
      id_prodejce: r.ID_PRODEJCE,
      dupKey: dupKey(date, cas, r.Kod || '', r.Doklad || ''),
    };
  });
}

function buildReport(symplioRows, dbRows, sim, fromIso, toIso) {
  const symByDup = new Map();
  for (const r of symplioRows) {
    const k = dupKey(r.date, r.cas, r.kod, r.doklad);
    if (!symByDup.has(k)) symByDup.set(k, []);
    symByDup.get(k).push(r);
  }

  const dokladAgg = new Map();
  for (const r of symplioRows) {
    if (!r.doklad || !r.kod) continue;
    const k = `${r.doklad}|${r.kod}`;
    if (!dokladAgg.has(k)) dokladAgg.set(k, { symplio: 0, db: 0, doklad: r.doklad, kod: r.kod });
    dokladAgg.get(k).symplio++;
  }
  for (const r of dbRows) {
    if (!r.doklad || !r.kod) continue;
    const k = `${r.doklad}|${r.kod}`;
    if (!dokladAgg.has(k)) dokladAgg.set(k, { symplio: 0, db: 0, doklad: r.doklad, kod: r.kod });
    dokladAgg.get(k).db++;
  }

  const mismatchedDoklady = [...dokladAgg.values()]
    .filter((x) => x.symplio !== x.db)
    .sort((a, b) => Math.abs(b.symplio - b.db) - Math.abs(a.symplio - a.db))
    .slice(0, 100);

  return {
    period: { from: fromIso, to: toIso },
    symplio_row_count: symplioRows.length,
    db_row_count: dbRows.length,
    symplio_dupkey_groups_with_multiple_lines: [...symByDup.values()].filter((a) => a.length > 1).length,
    actor_simulation: {
      would_insert: sim.wouldInsert,
      would_skip: sim.wouldSkip,
      skipped_samples: sim.skippedSamples,
    },
    doklad_kod_mismatch_count: mismatchedDoklady.length,
    doklad_kod_mismatch_top: mismatchedDoklady,
    sample_doklad_32604219001: {
      symplio: symplioRows.filter((r) => r.doklad === '32604219001'),
      db: dbRows.filter((r) => r.doklad === '32604219001'),
    },
    note: 'would_skip = řádky ze Symplia, které by současný actor přeskočil (dupKey: datum|čas|kód|doklad)',
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const reportsDir = args.out || path.join(__dirname, 'reports');
  fs.mkdirSync(reportsDir, { recursive: true });

  let xlsxPath = args.file;
  if (args.download || !xlsxPath) {
    xlsxPath = path.join(reportsDir, `symplio_${args.from}_${args.to}.xlsx`);
    await downloadXlsx(args.from, args.to, xlsxPath);
  }

  const { rows: symplioRows } = parseXlsx(xlsxPath);
  const inRange = symplioRows.filter((r) => r.date >= args.from && r.date <= args.to);
  console.log(`Symplio řádků v období: ${inRange.length}`);

  const sim = simulateActorSkip(inRange);

  if (!process.env.DB_PASSWORD) {
    throw new Error('Nastav DB_PASSWORD (nebo MYSQL_PASSWORD) pro připojení k DB');
  }
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
  });

  const dbRows = await loadDbRows(connection, args.from, args.to);
  await connection.end();
  console.log(`DB řádků v období: ${dbRows.length}`);

  const report = buildReport(inRange, dbRows, sim, args.from, args.to);
  const outFile = path.join(reportsDir, `compare_${args.from}_${args.to}.json`);
  fs.writeFileSync(outFile, JSON.stringify(report, null, 2), 'utf8');
  console.log(`Report: ${outFile}`);
  console.log(
    JSON.stringify(
      {
        symplio: report.symplio_row_count,
        db: report.db_row_count,
        would_skip: report.actor_simulation.would_skip,
        would_insert: report.actor_simulation.would_insert,
        multi_dupkey_groups: report.symplio_dupkey_groups_with_multiple_lines,
        doklad_kod_mismatches: report.doklad_kod_mismatch_count,
      },
      null,
      2,
    ),
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
