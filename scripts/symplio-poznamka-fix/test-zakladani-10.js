/**
 * Test 10 karet skladem z Katalog / !Import / PARTNER PL (kategorie 201).
 * Prázdného dodavatele nastaví na PARTNER PL (id 2). Nic jiného nemění.
 * stdout: JSON. Log na stderr.
 */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const LIMIT = 10;
const DODAVATEL_ID = '2';

const WORK = `
const callback = arguments[arguments.length - 1];
const LIMIT = arguments[0];
const DODAVATEL_ID = arguments[1];
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
function jeSklad(text) {
  const t = plain(text).toLowerCase();
  if (!t || t.includes('není') || t.includes('neni')) return false;
  const m = t.match(/(\\d+)/);
  return !!(m && Number(m[1]) > 0);
}
function grab(html, field) {
  const i = html.indexOf('data-name="' + field + '"');
  if (i < 0) return null;
  const tag = html.slice(i, i + 500);
  const pk = (tag.match(/data-pk="(\\d+)"/) || tag.match(/data-id="(\\d+)"/) || [])[1] || '';
  const crc = (tag.match(/data-crc="(\\d+)"/) || [])[1] || '';
  const value = (tag.match(/data-value="([^"]*)"/) || [])[1] || '';
  return { pk, crc, value };
}
async function saveItem(zbozi, field, meta, value) {
  const fd = new FormData();
  fd.append('name', field);
  fd.append('id', meta.pk);
  fd.append('crc', meta.crc);
  fd.append('value', value);
  const res = await fetch('/admin/w/Zbozi_Detail/saveItem/?zbozi=' + zbozi, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: fd
  });
  const text = await res.text();
  return { status: res.status, text: text.slice(0, 180) };
}
(async () => {
  const started = Date.now();
  const html = await fetch('/admin/kategorie-201/').then(r => r.text());
  if (html.includes('name="_username"')) {
    callback({ chyba: 'odhlaseno', ms: Date.now() - started });
    return;
  }
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const title = plain((doc.querySelector('title') || {}).textContent);
  if (![...doc.querySelectorAll('a[href*="zbozi-"]')].length) {
    callback({
      chyba: 'prazdny_vypis',
      title,
      delka: html.length,
      text: plain(doc.body.textContent).slice(0, 500),
      ms: Date.now() - started
    });
    return;
  }
  const ids = [];
  const seen = new Set();
  for (const a of doc.querySelectorAll('a[href*="zbozi-"]')) {
    const m = (a.getAttribute('href') || '').match(/zbozi-(\\d+)/);
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    ids.push({ id: m[1], nazev: plain(a.textContent).slice(0, 160) });
  }
  const hotovo = [];
  const mimo = [];
  for (const row of ids) {
    if (hotovo.length >= LIMIT) break;
    const page = await fetch('/admin/kategorie-201/zbozi-' + row.id).then(r => r.text());
    const pdoc = new DOMParser().parseFromString(page, 'text/html');
    const sklad = plain((pdoc.querySelector('.skladem-ks') || {}).textContent);
    const kod = (page.match(/\\bP\\d{4,}\\b/) || [])[0] || '';
    if (!jeSklad(sklad)) {
      mimo.push({ id: row.id, kod, sklad: sklad || 'neznámý' });
      continue;
    }
    const dod = grab(page, 'CZbozi.dodavatel_id');
    const item = {
      id: row.id, kod, nazev: row.nazev, sklad,
      dodavatel_pred: dod ? dod.value : null
    };
    if (dod && dod.pk && dod.crc && !dod.value) {
      item.ulozeni = await saveItem(row.id, 'CZbozi.dodavatel_id', dod, DODAVATEL_ID);
      const again = await fetch('/admin/kategorie-201/zbozi-' + row.id).then(r => r.text());
      const po = grab(again, 'CZbozi.dodavatel_id');
      item.dodavatel_po = po ? po.value : null;
    } else {
      item.ulozeni = null;
      item.dodavatel_po = dod ? dod.value : null;
      item.poznamka = dod && dod.value ? 'dodavatel už vyplněn' : 'pole dodavatele nenalezeno';
    }
    hotovo.push(item);
  }
  callback({
    ms: Date.now() - started,
    odkazu: ids.length,
    zpracovano: hotovo.length,
    mimo_sklad: mimo.length,
    polozky: hotovo
  });
})().catch(err => callback({ chyba: String(err) }));
`;

async function main() {
  const options = new chrome.Options();
  options.addArguments(
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--window-size=1920,1080',
    '--disable-blink-features=AutomationControlled',
  );
  if (process.env.HEADLESS === '1') options.addArguments('--headless=new');
  if (process.env.CHROME_BIN) options.setChromeBinaryPath(process.env.CHROME_BIN);
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  const started = Date.now();
  try {
    await driver.manage().setTimeouts({ script: 300000, pageLoad: 120000 });
    console.error('Přihlašuji se');
    await loginSymplio(driver, { store: 'globus' });
    await sleep(1000);
    console.error('Čtu kategorii 201, beru až 10 skladem');
    const result = await driver.executeAsyncScript(WORK, LIMIT, DODAVATEL_ID);
    result.celkem_ms = Date.now() - started;
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    if (result.chyba) process.exitCode = 1;
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
