#!/usr/bin/env node
const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const { loginSymplio, sleep } = require('./symplio-login');

async function login(driver) {
  await loginSymplio(driver);
}

async function main() {
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--headless=new');
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await login(driver);
    await driver.get('https://www.mobilmajak.cz/admin/doklady?code=32607037011&date_range%5Bfrom%5D=2026-01-01&date_range%5Bto%5D=2026-12-31');
    await sleep(5000);
    const paths = [
      '/admin/doklad/604419',
      '/admin/doklad/604419.json',
      '/admin/doklad/load/604419',
      '/admin/doklad/get?id=604419',
      '/admin/invoice/604419',
      '/admin/invoice/604419.json',
      '/admin/invoice/load/604419',
      '/admin/invoice/get?id=604419',
      '/admin/invoice/edit/604419',
      '/admin/uctenka/604419',
      '/admin/uctenka/604419.json',
    ];
    for (const p of paths) {
      const res = await driver.executeAsyncScript(`
        const cb = arguments[arguments.length - 1];
        fetch('${p}', { credentials: 'same-origin', headers: { Accept: 'application/json,text/html,*/*' } })
          .then(r => r.text().then(t => cb(JSON.stringify({ status: r.status, len: t.length, head: t.slice(0, 1200) }))))
          .catch(e => cb(JSON.stringify({ error: String(e) })));
      `);
      console.log('\n', p, res);
    }
  } finally {
    await driver.quit();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
