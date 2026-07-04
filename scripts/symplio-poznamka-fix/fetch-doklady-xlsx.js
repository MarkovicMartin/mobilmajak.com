#!/usr/bin/env node
/** Stáhne XLSX export dokladů (Invoice/Invoice) a vypíše hlavičky + poznámky u 32607037011. */
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const { loginSymplio, sleep } = require('./symplio-login');

async function main() {
  const from = process.argv[2] || '2026-07-01';
  const to = process.argv[3] || '2026-07-04';
  const options = new chrome.Options();
  options.addArguments('--no-sandbox', '--disable-dev-shm-usage', '--headless=new');
  const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
  try {
    await loginSymplio(driver);
    await driver.get('https://www.mobilmajak.cz/admin/doklady');
    await sleep(5000);
    const cookies = await driver.manage().getCookies();
    const cookieString = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
    const types = 'type%5B0%5D=faktura-faktura&type%5B1%5D=faktura-storno&type%5B2%5D=faktura-dobropis&type%5B3%5D=uctenka-uctenka&type%5B4%5D=uctenka-storno&type%5B5%5D=uctenka-dobropis&type%5B6%5D=buctenka-buctenka&type%5B7%5D=buctenka-storno&type%5B8%5D=buctenka-dobropis';
    const url = `https://www.mobilmajak.cz/admin/doklady?${types}&date_range%5Bfrom%5D=${from}&date_range%5Bto%5D=${to}&list-type=invoice-list&_export=xlsx`;
    const out = path.join(__dirname, 'reports', `doklady_${from}_${to}.xlsx`);
    for (let attempt = 1; attempt <= 3; attempt++) {
      const r = await axios.get(url, { responseType: 'arraybuffer', headers: { Cookie: cookieString } });
      const buf = Buffer.from(r.data);
      if (buf.slice(0, 2).toString('utf8') === 'PK') {
        fs.mkdirSync(path.dirname(out), { recursive: true });
        fs.writeFileSync(out, buf);
        console.log('Staženo', out, buf.length);
        const rows = XLSX.utils.sheet_to_json(XLSX.readFile(out).Sheets.Sheet1, { header: 1 });
        console.log('headers', rows[0]);
        const h = rows[0];
        const C = {}; h.forEach((x, i) => { if (x) C[x.toString().trim()] = i; });
        for (const row of rows.slice(1)) {
          const d = String(row[C.Doklad] || row[C['Kód']] || '');
          if (d.includes('32607037011')) {
            h.forEach((col, j) => { if (row[j] !== undefined && String(row[j]).trim()) console.log(col, row[j]); });
          }
        }
        return;
      }
      console.log('attempt', attempt, 'not xlsx', buf.length);
      await sleep(15000);
      await driver.get('https://www.mobilmajak.cz/admin/doklady');
      await sleep(5000);
    }
    throw new Error('XLSX export dokladů selhal');
  } finally {
    await driver.quit();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
