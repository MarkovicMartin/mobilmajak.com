/**
 * Změří karty výkupů v administraci Symplia.
 * stdin: {"kody":["V26100071",...]}
 * stdout: JSON pole měření. Log jen na stderr.
 */
const { loginSymplio, sleep } = require('../vykupy-actor/symplio-login');

function loadSelenium() {
  const { Builder } = require('selenium-webdriver');
  const chrome = require('selenium-webdriver/chrome');
  return { Builder, chrome };
}

function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.on('data', (c) => chunks.push(c));
    process.stdin.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('utf8').trim();
        resolve(raw ? JSON.parse(raw) : { kody: [] });
      } catch (err) {
        reject(err);
      }
    });
    process.stdin.on('error', reject);
  });
}

const INSPECT = `
const callback = arguments[arguments.length - 1];
const kody = arguments[0];
function plain(el) { return (el && el.textContent || '').replace(/\\s+/g, ' ').trim(); }
async function one(kod) {
  const searchHtml = await fetch('/admin/katalog/vyhledavani?p%5Bhledat%5D=' + encodeURIComponent(kod)).then(r => r.text());
  if (searchHtml.includes('name="_username"')) return { kod, nalezeno: false, chyba: 'odhlaseno' };
  const doc = new DOMParser().parseFromString(searchHtml, 'text/html');
  let hit = null;
  for (const a of doc.querySelectorAll('a[href*="zbozi-"]')) {
    const m = (a.getAttribute('href') || '').match(/kategorie-(\\d+)\\/zbozi-(\\d+)/);
    if (m) { hit = { cat: m[1], id: m[2], nazev: plain(a) }; break; }
  }
  if (!hit) return { kod, nalezeno: false };
  const [page, gal, par] = await Promise.all([
    fetch('/admin/kategorie-' + hit.cat + '/zbozi-' + hit.id).then(r => r.text()),
    fetch('/admin/w/Img_Galerie/display/?typ=zbozi&rel=' + hit.id).then(r => r.text()),
    fetch('/admin/w/Parametr_Vyplnit/display/?typ=zbozi&rel=' + hit.id).then(r => r.text())
  ]);
  const onPage = (page.match(/V\\d{5,}/) || [])[0] || '';
  if (onPage && onPage !== kod) return { kod, nalezeno: false, chyba: 'jiny_kod ' + onPage };
  const pdoc = new DOMParser().parseFromString(page, 'text/html');
  const stockText = plain(pdoc.querySelector('.skladem-ks'));
  const popisEl = pdoc.querySelector('[data-name="CZbozi.popis2"]');
  const photos = new Set([...gal.matchAll(/\\/(\\d+)\\.(?:jpg|jpeg|png|webp)/gi)].map(m => m[1])).size;
  const p2 = new DOMParser().parseFromString(par, 'text/html');
  let params = 0;
  for (const row of p2.querySelectorAll('.data-row')) {
    if (plain(row.querySelector('.data-value .edit, .data-value span'))) params++;
  }
  return {
    kod, nalezeno: true, cat: hit.cat, zbozi_id: hit.id, nazev: hit.nazev,
    stock_text: stockText, photos, params,
    popis_text_len: plain(popisEl).length,
    popis_ma_obrazek: !!(popisEl && popisEl.querySelector('img'))
  };
}
(async () => {
  const out = [];
  for (let i = 0; i < kody.length; i += 4) {
    const part = await Promise.all(kody.slice(i, i + 4).map(kod => one(kod).catch(err => ({ kod, nalezeno: false, chyba: String(err) }))));
    out.push(...part);
  }
  callback(out);
})();
`;

async function main() {
  const { kody } = await readStdin();
  const list = [...new Set((kody || []).map((k) => String(k).trim()).filter(Boolean))];
  if (!list.length) {
    process.stdout.write('[]\n');
    return;
  }
  const { Builder, chrome } = loadSelenium();
  const options = new chrome.Options();
  options.addArguments(
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
    '--window-size=1920,1080',
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  );
  if (process.env.HEADLESS !== '0') options.addArguments('--headless=new');
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await driver.manage().setTimeouts({ script: 180000 });
    console.error(`Přihlašuji se, karet ${list.length}`);
    await loginSymplio(driver, { store: 'hlavni_sklad' });
    await sleep(1000);
    const rows = [];
    for (let i = 0; i < list.length; i += 20) {
      const chunk = list.slice(i, i + 20);
      const part = await driver.executeAsyncScript(INSPECT, chunk);
      rows.push(...part);
      console.error(`Změřeno ${rows.length}/${list.length}`);
    }
    process.stdout.write(`${JSON.stringify(rows)}\n`);
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
