const { By } = require('selenium-webdriver');
const { loadSymplioCredentials } = require('./symplio-credentials');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function loginSymplio(driver, { selectGlobus = true } = {}) {
  const { user, pass } = loadSymplioCredentials();
  await driver.get('https://www.mobilmajak.cz/admin');
  await sleep(2000);
  await driver.findElement(By.name('_username')).sendKeys(user);
  await driver.findElement(By.name('_password')).sendKeys(pass);
  await driver.findElement(By.xpath("//button[@type='submit' and contains(., 'Přihlásit')]")).click();
  await sleep(3000);
  if (selectGlobus) {
    await driver.findElement(By.xpath("//a[contains(@class, 'btn-primary') and contains(., 'Globus')]")).click();
    await sleep(2000);
  }
}

module.exports = { loginSymplio, sleep };
