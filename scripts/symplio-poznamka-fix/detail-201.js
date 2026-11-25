/** Detail 17 karet skladem z kategorie 201. Nic nezapisuje. */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const IDS = process.argv.slice(2);

const WORK = `
const callback = arguments[arguments.length - 1];
const ids = arguments[0];
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
function grab(html, field) {
  const i = html.indexOf('data-name="' + field + '"');
  if (i < 0) return null;
  const tag = html.slice(i, i + 800);
  const value = (tag.match(/data-value="([^"]*)"/) || [])[1] || '';
  const text = plain(tag.replace(/<[^>]+>/g, ' ')).slice(0, 80);
  return { value, text };
}
(async () => {
  const out = [];
  for (const id of ids) {
    const page = await fetch('/admin/kategorie-201/zbozi-' + id).then(r => r.text());
    const gal = await fetch('/admin/w/Img_Galerie/display/?typ=zbozi&rel=' + id).then(r => r.text());
    const fotky = new Set([...gal.matchAll(/\\/(\\d+)\\.(?:jpg|jpeg|png|webp)/gi)].map(m => m[1])).size;
    const widget = await fetch('/admin/w/Zbozi_Kategorie/display/?zbozi=' + id).then(r => r.text());
    const doc = new DOMParser().parseFromString(widget, 'text/html');
    const cesty = [...doc.querySelectorAll('tr')].map(tr => {
      const radio = tr.querySelector('input[name=hlavni]');
      const tds = [...tr.querySelectorAll('td')];
      return radio ? plain(tds[1] ? tds[1].textContent : '') : null;
    }).filter(Boolean);
    const vyrobce = grab(page, 'CZbozi.vyrobce_id');
    const dod = grab(page, 'CZbozi.dodavatel_id');
    out.push({
      id,
      kod: (page.match(/\\bP\\d{4,}\\b/) || [])[0] || '',
      nazev: (grab(page, 'CZbozi.nazev') || {}).value || '',
      vyrobce: vyrobce ? vyrobce.value : '',
      vyrobceText: vyrobce ? vyrobce.text : '',
      dodavatel: dod ? dod.value : '',
      pokladna: (grab(page, 'CPolozka.prodejni') || {}).value || '',
      eshop: (grab(page, 'CPolozka.cena') || {}).value || '',
      vaha: (grab(page, 'CPolozka.vaha') || {}).value || '',
      fotky,
      cesty
    });
  }
  callback(out);
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
    const result = await driver.executeAsyncScript(WORK, IDS);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
