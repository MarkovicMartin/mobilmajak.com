/** Zjistí, jestli po straně 250 ještě něco je skladem. Nic nezapisuje. */
const path = require('path');
const { Builder } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const loginDir = process.env.SYMPLIO_SCRIPTS_DIR || path.join(__dirname, '../symplio-shared');
const { loginSymplio, sleep } = require(path.join(loginDir, 'symplio-login'));

const WORK = `
const callback = arguments[arguments.length - 1];
function plain(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
(async () => {
  const out = [];
  for (const page of [300, 500, 800, 1200, 1600]) {
    const html = await fetch('/admin/kategorie-201/?strana=' + page).then(r => r.text());
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const title = plain((doc.querySelector('title') || {}).textContent);
    const ids = new Set();
    for (const a of doc.querySelectorAll('a[href*="zbozi-"]')) {
      const m = (a.getAttribute('href') || '').match(/zbozi-(\\d+)/);
      if (m) ids.add(m[1]);
    }
    const skladem = (html.match(/[1-9]\\d*\\s*Skladem/gi) || []).length;
    out.push({ page, title, karet: ids.size, skladem, delka: html.length });
    if (!ids.size) break;
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
    await sleep(500);
    const result = await driver.executeAsyncScript(WORK);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await driver.quit();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
