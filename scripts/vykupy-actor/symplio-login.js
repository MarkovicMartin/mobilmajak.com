const { By, until } = require('selenium-webdriver');
const { loadSymplioCredentials } = require('./symplio-credentials');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function handleWafChallenge(driver) {
  try {
    const pageText = await driver.getPageSource();
    if (pageText.includes('WAF') || pageText.includes('Cloudflare') || pageText.includes('DDoS')) {
      console.log('Detekována WAF výzva, čekám...');
      await sleep(5000);
    }
  } catch (error) {
    console.log('Chyba při kontrole WAF:', error.message);
  }
}

async function selectStoreGlobus(driver) {
  const selectors = [
    "//a[contains(@class, 'btn-primary') and contains(., 'Globus')]",
    "//a[contains(@class, 'btn') and contains(., 'Globus')]",
    "//button[contains(@class, 'btn') and contains(., 'Globus')]",
  ];
  for (const xpath of selectors) {
    try {
      const el = await driver.wait(until.elementLocated(By.xpath(xpath)), 8000);
      await el.click();
      await sleep(2000);
      console.log('Vybrána prodejna Globus.');
      return;
    } catch (_) {
      // zkus další selektor
    }
  }
  const url = await driver.getCurrentUrl();
  if (!url.includes('/admin/login')) {
    console.log('Výběr Globus přeskočen – pravděpodobně už přihlášeno:', url);
    return;
  }
  throw new Error('Po přihlášení se nepodařilo vybrat prodejnu Globus');
}

async function loginSymplio(driver, { selectGlobus = true } = {}) {
  const { user, pass } = loadSymplioCredentials();
  await driver.get('https://www.mobilmajak.cz/admin');
  await handleWafChallenge(driver);
  await driver.wait(until.elementLocated(By.name('_username')), 30000);
  await driver.findElement(By.name('_username')).sendKeys(user);
  await driver.findElement(By.name('_password')).sendKeys(pass);
  await driver.findElement(By.xpath("//button[@type='submit' and contains(., 'Přihlásit')]")).click();
  await sleep(3000);
  await handleWafChallenge(driver);
  if (selectGlobus) {
    await selectStoreGlobus(driver);
    await sleep(1000);
    await handleWafChallenge(driver);
  }
}

module.exports = { loginSymplio, handleWafChallenge, sleep };
