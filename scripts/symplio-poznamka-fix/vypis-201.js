/** Výpis všech karet v kategorii 201. Nic nezapisuje. stdout: JSON. */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const WORK = `
const callback = arguments[arguments.length - 1];
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
(async () => {
  const started = Date.now();
  const seen = new Map();
  const stranky = [];
  let page = 1;
  let skladem = 0;
  while (page <= 250) {
    const url = '/admin/kategorie-201/' + (page > 1 ? '?strana=' + page : '');
    const html = await fetch(url).then(r => r.text());
    if (html.includes('name="_username"')) {
      callback({ chyba: 'odhlaseno' });
      return;
    }
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const links = [...doc.querySelectorAll('a[href*="zbozi-"]')];
    let nove = 0;
    for (const a of links) {
      const m = (a.getAttribute('href') || '').match(/zbozi-(\\d+)/);
      if (!m || seen.has(m[1])) continue;
      const tr = a.closest('tr');
      const rowText = plain(tr ? tr.textContent : a.parentElement ? a.parentElement.textContent : '');
      const ks = (rowText.match(/(\\d+)\\s*Skladem/i) || [])[1] || '0';
      const neni = /nen[ií]\\s*(dostupn|skladem)/i.test(rowText);
      const item = { id: m[1], nazev: plain(a.textContent).slice(0, 180), ks: neni ? '0' : ks };
      seen.set(m[1], item);
      if (item.ks !== '0') skladem++;
      nove++;
    }
    const dalsi = [...doc.querySelectorAll('a')].some(a => (a.getAttribute('href') || '').includes('strana=' + (page + 1)));
    if (page % 10 === 0) console.log('strana ' + page + ' celkem ' + seen.size + ' skladem ' + skladem);
    stranky.push({ page, nove, dalsi });
    if (!nove || !dalsi) break;
    page++;
  }
  const polozky = [...seen.values()].filter(p => p.ks !== '0');
  callback({ ms: Date.now() - started, pocet: seen.size, skladem: polozky.length, posledni: stranky[stranky.length - 1], polozky });
})().catch(err => callback({ chyba: String(err) }));
`;

async function main() {
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1920,1080');
  if (process.env.CHROME_BIN) options.setChromeBinaryPath(process.env.CHROME_BIN);
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await driver.manage().setTimeouts({ script: 420000, pageLoad: 120000 });
    await loginSymplio(driver, { store: 'globus' });
    await sleep(800);
    const result = await driver.executeAsyncScript(WORK);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    if (result.chyba) process.exitCode = 1;
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
