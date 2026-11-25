/**
 * Plné založení 3 jistých karet skladem z kategorie 201.
 * Bez vlastní fotky kartu do Ke kontrole nepřesouvá.
 * stdout: JSON. Log na stderr.
 */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const KARTY = [
  {
    id: '94395',
    kod: 'P94644',
    nazev: 'Tvrzené / ochranné sklo Apple iPhone 13 Pro Max černé - 5D Flexible Hybrid Glass',
    vyrobce: '33',
    dodavatel: '2',
    pokladna: '599',
    eshop: '199',
    vaha: '50',
    kratky: '<p>Tvrzené sklo 5D na Apple iPhone 13 Pro Max, černé. Má černý rámeček, kryje celou plochu a lepí po celé ploše.</p>',
    popis: '<p>Tvrzené sklo 5D na Apple iPhone 13 Pro Max, černé. Má černý rámeček, kryje celou plochu a lepí po celé ploše.</p><p>Sklo je určené pro Apple iPhone 13 Pro Max.</p>',
    list: '10181',
  },
  {
    id: '96731',
    kod: 'P96980',
    nazev: 'Pouzdro / obal na Samsung Galaxy A23 5G červené - knížkové Luna Book Gold',
    vyrobce: '33',
    dodavatel: '2',
    pokladna: '449',
    eshop: '199',
    vaha: '100',
    kratky: '<p>Knížkové pouzdro Luna Book Gold na Samsung Galaxy A23 5G, červené. Kryje displej i záda telefonu.</p>',
    popis: '<p>Knížkové pouzdro Luna Book Gold na Samsung Galaxy A23 5G, červené. Kryje displej i záda telefonu.</p><p>Pouzdro je určené pro Samsung Galaxy A23 5G.</p>',
    list: '12566',
  },
  {
    id: '114235',
    kod: 'P114501',
    nazev: 'Obal / kryt na Apple iPhone 15 broskvový - Silicone',
    vyrobce: '5',
    dodavatel: '2',
    pokladna: '349',
    eshop: '149',
    vaha: '100',
    kratky: '<p>Zadní kryt Silicone na Apple iPhone 15, broskvový.</p>',
    popis: '<p>Zadní kryt Silicone na Apple iPhone 15, broskvový.</p><p>Kryt je určený pro Apple iPhone 15.</p>',
    list: '13133',
  },
];

const WORK = `
const callback = arguments[arguments.length - 1];
const karty = arguments[0];
const KE_KONTROLE = '15563';
const IMPORT = '201';
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
function grab(html, field) {
  const i = html.indexOf('data-name="' + field + '"');
  if (i < 0) return null;
  const tag = html.slice(i, i + 700);
  const pk = (tag.match(/data-pk="(\\d+)"/) || tag.match(/data-id="(\\d+)"/) || [])[1] || '';
  const crc = (tag.match(/data-crc="(\\d+)"/) || [])[1] || '';
  return pk && crc ? { pk, crc } : null;
}
async function saveItem(zbozi, html, field, value) {
  const meta = grab(html, field);
  if (!meta) return { field, chyba: 'pole nenalezeno' };
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
  let ok = false;
  try { ok = JSON.parse(text).stav === 'ok'; } catch (_) {}
  return { field, ok, text: text.slice(0, 120) };
}
async function kategorie(zbozi, akce, id) {
  const res = await fetch('/admin/w/Zbozi_Kategorie/action/?zbozi=' + zbozi + '&akce=' + akce, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
    body: 'kategorie=' + id
  });
  const text = await res.text();
  let ok = false;
  try { ok = JSON.parse(text).stav === 'ok'; } catch (_) {}
  return { akce, id, ok, text: text.slice(0, 120) };
}
(async () => {
  const started = Date.now();
  const vysledky = [];
  for (const karta of karty) {
    const t0 = Date.now();
    let page = await fetch('/admin/kategorie-' + IMPORT + '/zbozi-' + karta.id).then(r => r.text());
    if (page.includes('name="_username"')) {
      vysledky.push({ kod: karta.kod, chyba: 'odhlaseno' });
      break;
    }
    const gal = await fetch('/admin/w/Img_Galerie/display/?typ=zbozi&rel=' + karta.id).then(r => r.text());
    const fotky = new Set([...gal.matchAll(/\\/(\\d+)\\.(?:jpg|jpeg|png|webp)/gi)].map(m => m[1])).size;
    const pole = [
      ['CZbozi.nazev', karta.nazev],
      ['CZbozi.vyrobce_id', karta.vyrobce],
      ['CZbozi.dodavatel_id', karta.dodavatel],
      ['CPolozka.prodejni', karta.pokladna],
      ['CPolozka.cena', karta.eshop],
      ['CPolozka.vaha', karta.vaha],
      ['CZbozi.popis', karta.kratky],
      ['CZbozi.popis2', karta.popis],
    ];
    const ulozeni = [];
    for (const [field, value] of pole) {
      const row = await saveItem(karta.id, page, field, value);
      ulozeni.push(row);
      if (row.ok) page = await fetch('/admin/kategorie-' + IMPORT + '/zbozi-' + karta.id).then(r => r.text());
    }
    const kat = [];
    kat.push(await kategorie(karta.id, 'add', karta.list));
    const presun = fotky > 0 && ulozeni.every(r => r.ok);
    if (presun) {
      kat.push(await kategorie(karta.id, 'add', KE_KONTROLE));
      kat.push(await kategorie(karta.id, 'main', KE_KONTROLE));
      kat.push(await kategorie(karta.id, 'delete', IMPORT));
    }
    const widget = await fetch('/admin/w/Zbozi_Kategorie/display/?zbozi=' + karta.id).then(r => r.text());
    const doc = new DOMParser().parseFromString(widget, 'text/html');
    const cesty = [...doc.querySelectorAll('tr')].map(tr => {
      const radio = tr.querySelector('input[name=hlavni]');
      const tds = [...tr.querySelectorAll('td')];
      return radio ? { id: radio.value, main: radio.checked, path: plain(tds[1] ? tds[1].textContent : '') } : null;
    }).filter(Boolean);
    vysledky.push({
      kod: karta.kod,
      id: karta.id,
      fotky,
      presunuto: presun,
      ms: Date.now() - t0,
      ulozeni,
      kat,
      cesty
    });
  }
  callback({ ms: Date.now() - started, vysledky });
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
  try {
    await driver.manage().setTimeouts({ script: 300000, pageLoad: 120000 });
    console.error('Přihlašuji se');
    await loginSymplio(driver, { store: 'globus' });
    await sleep(1000);
    console.error('Zakládám 3 karty');
    const result = await driver.executeAsyncScript(WORK, KARTY);
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
