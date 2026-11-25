/** Sundá zbylé složky !Import u tří testovacích karet. */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const MAZAT = [
  ['94395', '11290'],
  ['96731', '11351'],
  ['114235', '13112'],
];

const WORK = `
const callback = arguments[arguments.length - 1];
const pary = arguments[0];
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
(async () => {
  const out = [];
  for (const [zbozi, kat] of pary) {
    const res = await fetch('/admin/w/Zbozi_Kategorie/action/?zbozi=' + zbozi + '&akce=delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
      body: 'kategorie=' + kat
    });
    const text = await res.text();
    const widget = await fetch('/admin/w/Zbozi_Kategorie/display/?zbozi=' + zbozi).then(r => r.text());
    const doc = new DOMParser().parseFromString(widget, 'text/html');
    const cesty = [...doc.querySelectorAll('tr')].map(tr => {
      const radio = tr.querySelector('input[name=hlavni]');
      const tds = [...tr.querySelectorAll('td')];
      return radio ? { main: radio.checked, path: plain(tds[1] ? tds[1].textContent : '') } : null;
    }).filter(Boolean);
    out.push({ zbozi, text: text.slice(0, 80), cesty });
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
    await driver.manage().setTimeouts({ script: 120000, pageLoad: 120000 });
    await loginSymplio(driver, { store: 'globus' });
    await sleep(800);
    const result = await driver.executeAsyncScript(WORK, MAZAT);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
