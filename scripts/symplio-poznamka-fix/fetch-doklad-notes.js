#!/usr/bin/env node
/**
 * Stáhne mapu Doklad → Poznamka_dokladu ze Symplio seznamu dokladů.
 * Primárně HTML tabulka (/admin/doklady) – sloupec „Poznámky“ u Invoice/Invoice HTML config.
 * Záloha: XLSX export dokladů.
 */
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const { Builder, By, until } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const { loginSymplio, sleep } = require('./symplio-login');

const DOKLAD_TYPES =
  'type%5B0%5D=faktura-faktura&type%5B1%5D=faktura-storno&type%5B2%5D=faktura-dobropis' +
  '&type%5B3%5D=uctenka-uctenka&type%5B4%5D=uctenka-storno&type%5B5%5D=uctenka-dobropis' +
  '&type%5B6%5D=buctenka-buctenka&type%5B7%5D=buctenka-storno&type%5B8%5D=buctenka-dobropis';

const NOTE_HEADERS = [
  'Poznámky',
  'Poznámka k dokladu',
  'Poznámka dokladu',
  'Poznamka_dokladu',
  'Poznámka',
];

function parseArgs(argv) {
  const out = { out: path.join(__dirname, 'reports', 'poznamka_dokladu_enrichment.json') };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--from') out.from = argv[++i];
    else if (a === '--to') out.to = argv[++i];
    else if (a === '--out') out.out = argv[++i];
  }
  if (!out.from || !out.to) throw new Error('Chybí --from a --to');
  return out;
}

async function handleWafChallenge(driver) {
  try {
    const pageText = await driver.getPageSource();
    if (pageText.includes('WAF') || pageText.includes('Cloudflare') || pageText.includes('DDoS')) {
      console.log('WAF výzva – čekám...');
      await sleep(5000);
    }
  } catch (e) {
    console.log('WAF check:', e.message);
  }
}

function findColumnIndex(headers, names) {
  for (const name of names) {
    const idx = headers.findIndex(
      (h) => h && String(h).trim().toLowerCase() === name.toLowerCase(),
    );
    if (idx >= 0) return idx;
  }
  for (const name of names) {
    const idx = headers.findIndex(
      (h) => h && String(h).trim().toLowerCase().includes(name.toLowerCase()),
    );
    if (idx >= 0) return idx;
  }
  const pozIdx = headers.findIndex((h) => h && /poznám/i.test(String(h).trim()));
  return pozIdx;
}

function extractDokladCode(cell) {
  const m = String(cell || '').match(/(\d{9,})/);
  return m ? m[1] : null;
}

function dokladListUrl(from, to, page = 1) {
  let url =
    `https://www.mobilmajak.cz/admin/doklady?${DOKLAD_TYPES}` +
    `&date_range%5Bfrom%5D=${from}&date_range%5Bto%5D=${to}&list-type=invoice-list`;
  if (page > 1) url += `&strana=${page}`;
  return url;
}

async function readTablePage(driver) {
  await driver.wait(until.elementLocated(By.css('table thead th')), 20000);
  const headers = [];
  for (const th of await driver.findElements(By.css('table thead th'))) {
    headers.push((await th.getText()).replace(/\s+/g, ' ').trim());
  }
  const rows = [];
  for (const tr of await driver.findElements(By.css('table tbody tr'))) {
    const cells = [];
    for (const td of await tr.findElements(By.css('td'))) {
      cells.push((await td.getText()).replace(/\s+/g, ' ').trim());
    }
    let dokladFromLink = null;
    try {
      const links = await tr.findElements(By.css('a[href]'));
      for (const link of links) {
        const href = (await link.getAttribute('href')) || '';
        const text = (await link.getText()).replace(/\s+/g, ' ').trim();
        dokladFromLink =
          extractDokladCode(text) ||
          extractDokladCode(href) ||
          (href.match(/[?&]code=(\d{9,})/i) || [])[1] ||
          null;
        if (dokladFromLink) break;
      }
    } catch (_) {
      /* žádný odkaz v řádku */
    }
    if (cells.length) rows.push({ cells, dokladFromLink });
  }
  return { headers, rows };
}

function cellOffset(headers, cells) {
  if (!headers[0] && cells.length === headers.length + 1) return 1;
  if (!headers[0] && cells.length === headers.length) return 0;
  return 0;
}

function rowsToMap(headers, rowItems) {
  const pozIdx = findColumnIndex(headers, NOTE_HEADERS);
  const dokladIdx = findColumnIndex(headers, ['Doklad', 'Kód']);
  const nameIdx = findColumnIndex(headers, ['Název', 'Název dokladu']);
  const map = {};
  for (const item of rowItems) {
    const cells = item.cells || item;
    const offset = cellOffset(headers, cells);
    const getCell = (idx) => (idx >= 0 ? (cells[idx + offset] || '') : '');
    const dokladRaw = dokladIdx >= 0 ? getCell(dokladIdx) : null;
    const nameRaw = nameIdx >= 0 ? getCell(nameIdx) : null;
    const doklad =
      item.dokladFromLink ||
      (dokladRaw ? String(dokladRaw).trim() : null) ||
      extractDokladCode(nameRaw);
    const note = pozIdx >= 0 ? getCell(pozIdx).trim() : '';
    if (doklad && note) map[String(doklad).trim()] = note;
  }
  return { map, pozIdx, dokladIdx, nameIdx };
}

function mergeMaps(into, from) {
  for (const [k, v] of Object.entries(from)) {
    if (v) into[k] = v;
  }
  return into;
}

async function fetchDokladNotesMapHtml(driver, from, to) {
  const map = {};
  let page = 1;
  let pozIdx = -1;

  while (true) {
    const url = dokladListUrl(from, to, page);
    await driver.get(url);
    await sleep(4000);
    await handleWafChallenge(driver);

    const { headers, rows } = await readTablePage(driver);
    if (page === 1) {
      pozIdx = findColumnIndex(headers, NOTE_HEADERS);
      console.log(`HTML strana ${page}: ${rows.length} řádků, pozIdx=${pozIdx}, headers=${headers.join(' | ')}`);
    } else {
      console.log(`HTML strana ${page}: ${rows.length} řádků`);
    }

    if (pozIdx < 0) {
      console.warn('Sloupec Poznámky v HTML tabulce nenalezen');
      break;
    }

    const parsed = rowsToMap(headers, rows);
    mergeMaps(map, parsed.map);

    const nextLinks = await driver.findElements(
      By.xpath(`//a[contains(@href,'strana=${page + 1}')]`),
    );
    if (!nextLinks.length || rows.length === 0) break;
    page += 1;
  }

  return { map, pozIdx, pages: page };
}

async function downloadDokladyXlsxBuffer(driver, from, to) {
  await driver.get(dokladListUrl(from, to));
  await sleep(4000);
  await handleWafChallenge(driver);
  const cookies = await driver.manage().getCookies();
  const cookieString = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
  const url = `${dokladListUrl(from, to)}&_export=xlsx`;

  for (let attempt = 1; attempt <= 3; attempt++) {
    if (attempt > 1) {
      console.log(`Opakování XLSX (${attempt}/3)...`);
      await driver.get(dokladListUrl(from, to));
      await sleep(5000);
      await handleWafChallenge(driver);
    }
    const r = await axios.get(url, {
      responseType: 'arraybuffer',
      headers: {
        Cookie: cookieString,
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
      },
      timeout: 120000,
    });
    const buf = Buffer.from(r.data);
    if (buf.slice(0, 2).toString('utf8') === 'PK') {
      console.log(`XLSX staženo (${buf.length} B)`);
      return buf;
    }
    console.warn(`Pokus ${attempt}: odpověď není XLSX (${buf.length} B)`);
    await sleep(10000);
  }
  throw new Error('XLSX export dokladů selhal');
}

function parseDokladNotesFromXlsxBuffer(buf) {
  const wb = XLSX.read(buf, { type: 'buffer' });
  const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null });
  const headers = (rows[0] || []).map((h) => (h != null ? String(h).trim() : ''));
  const pozIdx = findColumnIndex(headers, NOTE_HEADERS);
  console.log(`XLSX: ${Math.max(0, rows.length - 1)} řádků, pozIdx=${pozIdx}, headers=${headers.join(' | ')}`);
  return rowsToMap(headers, rows.slice(1)).map;
}

/**
 * @param {import('selenium-webdriver').WebDriver} driver přihlášený driver
 * @param {string} from YYYY-MM-DD
 * @param {string} to YYYY-MM-DD
 * @returns {Promise<Record<string, string>>}
 */
async function fetchDokladNotesMap(driver, from, to) {
  const html = await fetchDokladNotesMapHtml(driver, from, to);
  if (html.pozIdx >= 0 && Object.keys(html.map).length > 0) {
    console.log(`HTML scrape: ${Object.keys(html.map).length} poznámek (${html.pages} str.)`);
    return html.map;
  }

  if (html.pozIdx >= 0 && Object.keys(html.map).length === 0) {
    console.log('HTML scrape: sloupec nalezen, ale žádná neprázdná poznámka');
    return html.map;
  }

  console.log('HTML scrape selhal – zkouším XLSX...');
  const buf = await downloadDokladyXlsxBuffer(driver, from, to);
  return parseDokladNotesFromXlsxBuffer(buf);
}

async function main() {
  const args = parseArgs(process.argv);
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--headless=new');
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();

  let map = {};
  try {
    await loginSymplio(driver);
    map = await fetchDokladNotesMap(driver, args.from, args.to);
  } finally {
    await driver.quit();
  }

  fs.mkdirSync(path.dirname(args.out), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify({
    created_at: new Date().toISOString(),
    period: { from: args.from, to: args.to },
    count: Object.keys(map).length,
    map,
  }, null, 2));
  console.log(`Uloženo ${Object.keys(map).length} poznámek → ${args.out}`);
  for (const [d, n] of Object.entries(map).slice(0, 10)) {
    console.log(`  ${d}: ${n.slice(0, 80)}`);
  }
  if (map['32607037011']) console.log('32607037011:', map['32607037011']);
}

module.exports = {
  fetchDokladNotesMap,
  fetchDokladNotesMapHtml,
  parseDokladNotesFromXlsxBuffer,
  extractDokladCode,
  readTablePage,
};

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
