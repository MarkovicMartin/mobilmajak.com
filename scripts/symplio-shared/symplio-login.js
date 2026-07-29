/**
 * Sdílené Symplio přihlášení (WAF + robustní výběr prodejny/skladu).
 *
 *   loginSymplio(driver, { store: 'globus' | 'hlavni_sklad' | string | null })
 *
 * Legacy: { selectGlobus: true|false } → store 'globus' / null.
 *
 * Důležité: nepoužívat driver.wait(until.*) – Condition objekty z jiné kopie
 * selenium-webdriver (shared symlink vs actor node_modules) padají s
 * "Wait condition must be a promise-like object". By bereme z cwd actoru.
 */
const path = require('path');
const { loadSymplioCredentials } = require('./symplio-credentials');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function loadBy() {
  const candidates = [process.cwd(), path.dirname(require.main?.filename || '')].filter(Boolean);
  try {
    const resolved = require.resolve('selenium-webdriver', { paths: candidates });
    return require(resolved).By;
  } catch (_) {
    return require('selenium-webdriver').By;
  }
}

const By = loadBy();

const STORE_LABELS = {
  globus: 'Globus',
  hlavni_sklad: 'Hlavní sklad',
};

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

function resolveStoreLabel(store) {
  if (store == null || store === false) return null;
  if (typeof store === 'string') {
    const key = store.trim().toLowerCase().replace(/\s+/g, '_');
    if (STORE_LABELS[key]) return STORE_LABELS[key];
    if (store.trim()) return store.trim();
  }
  return null;
}

/**
 * Polling místo until.elementLocated – funguje napříč verzemi Selenium.
 * @param {import('selenium-webdriver').WebDriver} driver
 * @param {import('selenium-webdriver').Locator} locator
 */
async function waitForElements(driver, locator, timeoutMs = 30000, pollMs = 250) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const els = await driver.findElements(locator);
      if (els.length) return els;
    } catch (err) {
      lastErr = err;
    }
    await sleep(pollMs);
  }
  const detail = lastErr ? ` (${lastErr.message})` : '';
  throw new Error(`Timeout ${timeoutMs}ms waiting for elements${detail}`);
}

/**
 * @param {import('selenium-webdriver').WebDriver} driver
 * @param {string} storeLabel
 */
async function selectStore(driver, storeLabel) {
  if (!storeLabel) return;

  const selectors = [
    `//a[contains(@class, 'btn-primary') and contains(., '${storeLabel}')]`,
    `//a[contains(@class, 'btn') and contains(., '${storeLabel}')]`,
    `//button[contains(@class, 'btn') and contains(., '${storeLabel}')]`,
    `//a[contains(., '${storeLabel}')]`,
  ];
  for (const xpath of selectors) {
    try {
      const els = await waitForElements(driver, By.xpath(xpath), 8000);
      await els[0].click();
      await sleep(2000);
      console.log(`Vybráno: ${storeLabel}`);
      return;
    } catch (_) {
      // zkus další selektor
    }
  }
  const url = await driver.getCurrentUrl();
  if (!url.includes('/admin/login')) {
    console.log(`Výběr „${storeLabel}“ přeskočen – pravděpodobně už přihlášeno:`, url);
    return;
  }
  throw new Error(`Po přihlášení se nepodařilo vybrat: ${storeLabel}`);
}

/**
 * @param {import('selenium-webdriver').WebDriver} driver
 * @param {{ store?: string|null, selectGlobus?: boolean }} [opts]
 */
async function loginSymplio(driver, opts = {}) {
  let store = opts.store;
  if (store === undefined) {
    if (opts.selectGlobus === false) store = null;
    else store = 'globus';
  }
  const storeLabel = resolveStoreLabel(store);

  await driver.get('https://www.mobilmajak.cz/admin');
  await handleWafChallenge(driver);

  const usernameFields = await driver.findElements(By.name('_username'));
  if (usernameFields.length) {
    const { user, pass } = loadSymplioCredentials();
    await usernameFields[0].sendKeys(user);
    await driver.findElement(By.name('_password')).sendKeys(pass);
    await driver.findElement(By.xpath("//button[@type='submit' and contains(., 'Přihlásit')]")).click();
    await sleep(3000);
    await handleWafChallenge(driver);
  } else {
    console.log('Přihlašovací formulář nenalezen – pokračuji (už přihlášeno?).');
  }

  if (storeLabel) {
    await selectStore(driver, storeLabel);
    await sleep(1000);
    await handleWafChallenge(driver);
  }
}

module.exports = {
  loginSymplio,
  handleWafChallenge,
  selectStore,
  sleep,
  resolveStoreLabel,
  waitForElements,
};
