#!/usr/bin/env node
/**
 * Zapíše jisté kategorie do Symplia.
 * stdin: {"polozky":[{"kod":"P1","kategorie":[15555]}]}
 * stdout: {"zapsano":N,"preskoceno":N}
 * Nejistý kód se sem vůbec nedostane. Když se list nepodaří nastavit, kód se přeskočí.
 */
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const { loginSymplio, sleep } = require('./symplio-login');

const PRACOVNI = [
  'Nově naskladněno',
  'ZALOŽENO RUČNĚ',
  'Zakládání',
  '!Import',
  '!SKLAD',
  'Bordel_neni_skladem',
];

function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.on('data', (c) => chunks.push(c));
    process.stdin.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('utf8').trim();
        resolve(raw ? JSON.parse(raw) : { polozky: [] });
      } catch (err) {
        reject(err);
      }
    });
    process.stdin.on('error', reject);
  });
}

const ZAPIS = `
const callback = arguments[arguments.length - 1];
const polozky = arguments[0];
const pracovni = arguments[1];
function plain(el) { return (el && el.textContent || '').replace(/\\s+/g, ' ').trim(); }
async function post(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body,
  });
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch (e) { data = null; }
  return { ok: res.ok && data && data.stav !== 'error' && !/Nelze nastavit/.test(text), text: text.slice(0, 180) };
}
async function jeden(item) {
  const kod = item.kod;
  const cile = (item.kategorie || []).map(String);
  if (!kod || !cile.length) return { kod, stav: 'preskoceno', duvod: 'prazdne' };
  const searchHtml = await fetch('/admin/katalog/vyhledavani?p%5Bhledat%5D=' + encodeURIComponent(kod)).then(r => r.text());
  if (searchHtml.includes('name="_username"')) return { kod, stav: 'preskoceno', duvod: 'odhlaseno' };
  const doc = new DOMParser().parseFromString(searchHtml, 'text/html');
  let zbozi = '';
  let odkaz = '';
  for (const a of doc.querySelectorAll('a[href*="zbozi-"]')) {
    const href = a.getAttribute('href') || '';
    const m = href.match(/kategorie-(\\d+)\\/zbozi-(\\d+)/);
    if (m) { odkaz = '/admin/kategorie-' + m[1] + '/zbozi-' + m[2]; zbozi = m[2]; break; }
  }
  if (!zbozi) return { kod, stav: 'preskoceno', duvod: 'nenalezeno' };
  const page = await fetch(odkaz).then(r => r.text());
  const naStrance = (page.match(/\\b[PV]\\d{5,}\\b/) || [])[0] || '';
  if (naStrance !== kod) return { kod, stav: 'preskoceno', duvod: 'jiny_kod' };
  for (const id of cile) {
    const add = await post('/admin/w/Zbozi_Kategorie/action/?zbozi=' + zbozi + '&akce=add', 'kategorie=' + id);
    if (!add.ok && !/již|jiz|exist/i.test(add.text)) return { kod, stav: 'preskoceno', duvod: 'add' };
  }
  const main = await post('/admin/w/Zbozi_Kategorie/action/?zbozi=' + zbozi + '&akce=main', 'kategorie=' + cile[0]);
  if (!main.ok) return { kod, stav: 'preskoceno', duvod: 'main' };
  const widget = await fetch('/admin/w/Zbozi_Kategorie/display/?zbozi=' + zbozi).then(r => r.text());
  const wdoc = new DOMParser().parseFromString(widget, 'text/html');
  for (const input of wdoc.querySelectorAll('input[type=radio]')) {
    const id = String(input.value || '');
    if (!id || cile.includes(id)) continue;
    const row = input.closest('tr, li, .row') || input.parentElement;
    const text = plain(row);
    const segmenty = text.split('/').map(s => s.replace(/^Smazat\\s+/, '').trim());
    if (!segmenty.some(s => pracovni.includes(s)) && !pracovni.includes(text.replace(/^Smazat\\s+/, '').trim())) continue;
    await post('/admin/w/Zbozi_Kategorie/action/?zbozi=' + zbozi + '&akce=delete', 'kategorie=' + id);
  }
  return { kod, stav: 'zapsano', zbozi };
}
(async () => {
  const out = [];
  for (const item of polozky) {
    try { out.push(await jeden(item)); }
    catch (err) { out.push({ kod: item.kod, stav: 'preskoceno', duvod: String(err).slice(0, 120) }); }
  }
  callback(out);
})();
`;

async function main() {
  const { polozky } = await readStdin();
  const list = Array.isArray(polozky) ? polozky : [];
  if (!list.length) {
    process.stdout.write('{"zapsano":0,"preskoceno":0}\n');
    return;
  }
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
    await driver.manage().setTimeouts({ script: 300000 });
    console.error(`Přihlašuji se, položek ${list.length}`);
    await loginSymplio(driver, { store: 'globus' });
    await sleep(1000);
    const rows = await driver.executeAsyncScript(ZAPIS, list, PRACOVNI);
    const zapsano = rows.filter((r) => r.stav === 'zapsano').length;
    const preskoceno = rows.length - zapsano;
    for (const row of rows) {
      if (row.stav !== 'zapsano') console.error(`přeskočeno ${row.kod} (${row.duvod || ''})`);
    }
    process.stdout.write(`${JSON.stringify({ zapsano, preskoceno })}\n`);
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
