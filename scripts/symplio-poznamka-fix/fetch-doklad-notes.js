#!/usr/bin/env node
/**
 * Stáhne mapu Doklad → Poznamka_dokladu ze Symplio seznamu dokladů (HTML tabulka).
 * Vyžaduje sloupec „Poznámky“ v /admin/admin-table-config/edit/html?code=Invoice/Invoice
 *
 *   node fetch-doklad-notes.js --from 2026-07-01 --to 2026-07-04 --out reports/poznamka_dokladu_enrichment.json
 */
const fs = require('fs');
const path = require('path');
const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const { loginSymplio, sleep } = require('./symplio-login');

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

async function readTablePage(driver) {
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
    if (cells.length) rows.push(cells);
  }
  return { headers, rows };
}

function extractDokladCode(nameCell) {
  const m = String(nameCell || '').match(/(\d{9,})/);
  return m ? m[1] : null;
}

/**
 * @param {import('selenium-webdriver').WebDriver} driver přihlášený driver
 * @param {string} from YYYY-MM-DD
 * @param {string} to YYYY-MM-DD
 * @returns {Promise<Record<string, string>>}
 */
async function fetchDokladNotesMap(driver, from, to) {
  const map = {};
  let url = `https://www.mobilmajak.cz/admin/doklady?date_range%5Bfrom%5D=${from}&date_range%5Bto%5D=${to}`;
  let page = 1;

  while (url) {
    await driver.get(url);
    await sleep(5000);
    const { headers, rows } = await readTablePage(driver);
    const pozIdx = headers.findIndex((h) => /^poznámky$/i.test(h));
    const nameIdx = headers.findIndex((h) => /^název$/i.test(h));
    console.log(`Strana ${page}: ${rows.length} řádků, headers=${headers.join(' | ')}, pozIdx=${pozIdx}`);

    for (const cells of rows) {
      const doklad = extractDokladCode(cells[nameIdx >= 0 ? nameIdx : 1]);
      const note = pozIdx >= 0 ? (cells[pozIdx] || '').trim() : '';
      if (doklad && note) map[doklad] = note;
    }

    const nextLinks = await driver.findElements(By.xpath("//a[contains(@href,'strana=') and contains(., '›')] | //a[contains(@href,'strana=') and normalize-space(text())='»'] | //a[contains(@href,'strana=') and contains(@class,'next')]"));
    let nextHref = null;
    for (const link of nextLinks) {
      const href = await link.getAttribute('href');
      if (href && href.includes(`strana=${page + 1}`)) {
        nextHref = href;
        break;
      }
    }
    if (!nextHref) {
      const all = await driver.findElements(By.xpath(`//a[contains(@href,'strana=${page + 1}')]`));
      if (all.length) nextHref = await all[0].getAttribute('href');
    }
    if (nextHref) {
      url = nextHref.startsWith('http') ? nextHref : `https://www.mobilmajak.cz${nextHref.replace(/&amp;/g, '&')}`;
      page += 1;
    } else {
      url = null;
    }
  }

  return map;
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
  const sample = Object.entries(map).slice(0, 10);
  for (const [d, n] of sample) console.log(`  ${d}: ${n.slice(0, 80)}`);
}

module.exports = {
  fetchDokladNotesMap,
  readTablePage,
  extractDokladCode,
};

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
