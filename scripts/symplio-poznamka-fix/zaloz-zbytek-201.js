/**
 * Založí 3 jisté karty skladem a prázdného dodavatele doplní u dvou dalších.
 * Kartu bez fotky nebo se špatným listem do Ke kontrole nepřesouvá.
 */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const KARTY = [
  {
    id: '102902',
    kod: 'P103151',
    nazev: 'Pouzdro / obal na Samsung Galaxy S23 zlaté - knížkové Luna Book Gold',
    vyrobce: '33',
    dodavatel: '2',
    pokladna: '449',
    eshop: '199',
    vaha: '100',
    kratky: '<p>Knížkové pouzdro Luna Book Gold na Samsung Galaxy S23, zlaté. Kryje displej i záda telefonu.</p>',
    popis: '<p>Knížkové pouzdro Luna Book Gold na Samsung Galaxy S23, zlaté. Kryje displej i záda telefonu.</p><p>Pouzdro je určené pro Samsung Galaxy S23.</p>',
    listy: ['12572'],
  },
  {
    id: '127678',
    kod: 'P127947',
    nazev: 'Tvrzené / ochranné sklo Xiaomi Redmi Note 13 5G / Redmi Note 13 Pro 4G - 9H',
    vyrobce: '310',
    dodavatel: '2',
    pokladna: '399',
    eshop: '149',
    vaha: '50',
    kratky: '<p>Tvrzené sklo 9H na Xiaomi Redmi Note 13 5G a Redmi Note 13 Pro 4G. Je tvrdé, kryje zobrazovací část, není až do krajů a lepí po celé ploše.</p>',
    popis: '<p>Tvrzené sklo 9H na Xiaomi Redmi Note 13 5G a Redmi Note 13 Pro 4G. Je tvrdé, kryje zobrazovací část, není až do krajů a lepí po celé ploše.</p><p>Sklo je určené pro Xiaomi Redmi Note 13 5G a Xiaomi Redmi Note 13 Pro 4G.</p>',
    listy: ['13475', '13507'],
  },
  {
    id: '134950',
    kod: 'P135221',
    nazev: 'Tvrzené / ochranné sklo Apple iPhone 17 Pro Max - Flexible Nano',
    vyrobce: '33',
    dodavatel: '2',
    pokladna: '399',
    eshop: '199',
    vaha: '50',
    kratky: '<p>Ochranná fólie Flexible Nano na Apple iPhone 17 Pro Max. Kryje téměř celou plochu displeje.</p>',
    popis: '<p>Ochranná fólie Flexible Nano na Apple iPhone 17 Pro Max. Kryje téměř celou plochu displeje.</p><p>Fólie je určená pro Apple iPhone 17 Pro Max.</p>',
    listy: ['15234'],
  },
];

const JEN_DODAVATEL = ['127676', '128989'];

const WORK = `
const callback = arguments[arguments.length - 1];
const karty = arguments[0];
const jenDodavatel = arguments[1];
const KE = '15563';
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
  if (!meta) return { field, ok: false, chyba: 'pole nenalezeno' };
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
  return { field, ok, text: text.slice(0, 80) };
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
  return { akce, id, ok };
}
async function cesty(zbozi) {
  const widget = await fetch('/admin/w/Zbozi_Kategorie/display/?zbozi=' + zbozi).then(r => r.text());
  const doc = new DOMParser().parseFromString(widget, 'text/html');
  return [...doc.querySelectorAll('tr')].map(tr => {
    const radio = tr.querySelector('input[name=hlavni]');
    const tds = [...tr.querySelectorAll('td')];
    return radio ? { id: radio.value, main: radio.checked, path: plain(tds[1] ? tds[1].textContent : '') } : null;
  }).filter(Boolean);
}
(async () => {
  const vysledky = [];
  for (const karta of karty) {
    let page = await fetch('/admin/kategorie-201/zbozi-' + karta.id).then(r => r.text());
    if (page.includes('name="_username"')) {
      vysledky.push({ kod: karta.kod, chyba: 'odhlaseno' });
      break;
    }
    const gal = await fetch('/admin/w/Img_Galerie/display/?typ=zbozi&rel=' + karta.id).then(r => r.text());
    const fotky = new Set([...gal.matchAll(/\\/(\\d+)\\.(?:jpg|jpeg|png|webp)/gi)].map(m => m[1])).size;
    const ulozeni = [];
    for (const [field, value] of [
      ['CZbozi.nazev', karta.nazev],
      ['CZbozi.vyrobce_id', karta.vyrobce],
      ['CZbozi.dodavatel_id', karta.dodavatel],
      ['CPolozka.prodejni', karta.pokladna],
      ['CPolozka.cena', karta.eshop],
      ['CPolozka.vaha', karta.vaha],
      ['CZbozi.popis', karta.kratky],
      ['CZbozi.popis2', karta.popis],
    ]) {
      const row = await saveItem(karta.id, page, field, value);
      ulozeni.push(row);
      if (row.ok) page = await fetch('/admin/kategorie-201/zbozi-' + karta.id).then(r => r.text());
    }
    const kat = [];
    for (const list of karta.listy) kat.push(await kategorie(karta.id, 'add', list));
    let po = await cesty(karta.id);
    const listyOk = karta.listy.every(id => po.some(c => c.id === id && c.path.includes('PŘÍSLUŠENSTVÍ')));
    const presun = fotky > 0 && ulozeni.every(r => r.ok) && listyOk;
    if (presun) {
      kat.push(await kategorie(karta.id, 'add', KE));
      kat.push(await kategorie(karta.id, 'main', KE));
      po = await cesty(karta.id);
      for (const c of po) {
        if (c.path.startsWith('!Import')) kat.push(await kategorie(karta.id, 'delete', c.id));
      }
      po = await cesty(karta.id);
    }
    vysledky.push({ kod: karta.kod, id: karta.id, fotky, listyOk, presunuto: presun, ulozeni, kat, cesty: po });
  }
  const dod = [];
  for (const id of jenDodavatel) {
    let page = await fetch('/admin/kategorie-201/zbozi-' + id).then(r => r.text());
    const row = await saveItem(id, page, 'CZbozi.dodavatel_id', '2');
    dod.push({ id, ...row });
  }
  callback({ vysledky, dod });
})().catch(err => callback({ chyba: String(err) }));
`;

async function main() {
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1920,1080');
  if (process.env.CHROME_BIN) options.setChromeBinaryPath(process.env.CHROME_BIN);
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await driver.manage().setTimeouts({ script: 180000, pageLoad: 120000 });
    await loginSymplio(driver, { store: 'globus' });
    await sleep(600);
    const result = await driver.executeAsyncScript(WORK, KARTY, JEN_DODAVATEL);
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
