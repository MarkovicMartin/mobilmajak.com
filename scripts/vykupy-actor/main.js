const { Actor } = require('apify');
const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const mysql = require('mysql2/promise');
const { loginSymplio, handleWafChallenge, sleep } = require('./symplio-login');

function mysqlConfig() {
  return {
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    password: process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD || '',
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
  };
}

async function connectToMySQL() {
  console.log('Připojuji se k MySQL databázi...');
  const connection = await mysql.createConnection(mysqlConfig());
  console.log('Úspěšně připojen k MySQL databázi');
  return connection;
}

async function getUsersMap(connection) {
  console.log('Načítám uživatele z WEB_USERS...');
  const [rows] = await connection.execute('SELECT id, jmeno, prijmeni FROM WEB_USERS');
  const userMap = {};
  rows.forEach((row) => {
    userMap[`${row.jmeno} ${row.prijmeni}`.trim()] = row.id;
  });
  console.log(`Načteno ${rows.length} uživatelů.`);
  return userMap;
}

async function getStoresMap(connection) {
  console.log('Načítám prodejny z WEB_PRODEJNY...');
  const [rows] = await connection.execute('SELECT id, nazev FROM WEB_PRODEJNY');
  const storeMap = {};
  rows.forEach((row) => {
    storeMap[row.nazev.trim()] = row.id;
  });
  console.log(`Načteno ${rows.length} prodejen.`);
  return storeMap;
}

async function downloadFileWithAxios(url, cookies, outputPath) {
  console.log(`Stahování souboru z URL: ${url}`);
  const response = await axios({
    method: 'GET',
    url,
    responseType: 'arraybuffer',
    headers: {
      Cookie: cookies,
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    },
  });
  fs.writeFileSync(outputPath, response.data);
  console.log(`Soubor úspěšně stažen do: ${outputPath}`);
  return true;
}

function formatDateISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function parseDateISO(value) {
  const d = new Date(`${value}T12:00:00`);
  if (Number.isNaN(d.getTime())) {
    throw new Error(`Neplatné datum: ${value}`);
  }
  return d;
}

function resolveTargetDates() {
  const from = process.env.BACKFILL_FROM || process.env.TARGET_DATE;
  const to = process.env.BACKFILL_TO || process.env.TARGET_DATE;
  if (from) {
    const start = parseDateISO(from);
    const end = parseDateISO(to || from);
    const dates = [];
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      dates.push(formatDateISO(new Date(d)));
    }
    console.log(`Backfill období: ${dates[0]} – ${dates[dates.length - 1]} (${dates.length} dní)`);
    return dates;
  }
  return [formatDateISO(new Date())];
}

async function setupCheckbox(driver, text, targetState) {
  try {
    const xpath = `//span[@class='lbl' and contains(normalize-space(), '${text}')]/ancestor::label`;
    const label = await driver.findElement(By.xpath(xpath));
    const checkbox = await label.findElement(By.css('input[type="checkbox"]'));
    if ((await checkbox.isSelected()) !== targetState) {
      await label.click();
      console.log(`Checkbox "${text}" změněn na ${targetState}`);
    }
  } catch (e) {
    console.log(`Nepodařilo se nastavit checkbox "${text}":`, e.message);
  }
}

async function processDay(driver, connection, usersMap, storesMap, dateISO, downloadDir) {
  console.log(`\n=== Zpracovávám den ${dateISO} ===`);
  await driver.get('https://www.mobilmajak.cz/admin/sklady/doklady/polozky');
  await sleep(5000);
  await handleWafChallenge(driver);

  await setupCheckbox(driver, 'výdejka', false);
  await setupCheckbox(driver, 'převodka', false);
  await setupCheckbox(driver, 'příjemka', true);

  try {
    let fromInput = null;
    let toInput = null;
    try {
      fromInput = await driver.findElement(By.id('date_range_from'));
      toInput = await driver.findElement(By.id('date_range_to'));
    } catch (_) {
      try {
        fromInput = await driver.findElement(By.name('date_range_from'));
        toInput = await driver.findElement(By.name('date_range_to'));
      } catch (_2) {
        const dateInputs = await driver.findElements(By.css("input[type='date']"));
        if (dateInputs.length >= 2) {
          fromInput = dateInputs[0];
          toInput = dateInputs[1];
        }
      }
    }
    if (fromInput && toInput) {
      await fromInput.clear();
      await driver.executeScript(`arguments[0].value = '${dateISO}';`, fromInput);
      await toInput.clear();
      await driver.executeScript(`arguments[0].value = '${dateISO}';`, toInput);
    }
    try {
      const itemInput = await driver.findElement(By.id('item'));
      await itemInput.clear();
      await itemInput.sendKeys('bazar');
    } catch (_) {
      console.log('Pole item nenalezeno, pokračuji přes URL export.');
    }
    await sleep(1000);
    try {
      const filterBtn = await driver.findElement(
        By.xpath("//button[contains(@class, 'btn-primary') and contains(., 'Filtrovat')]"),
      );
      await filterBtn.click();
      await sleep(5000);
    } catch (_) {
      console.log('Tlačítko Filtrovat nenalezeno, pokračuji přes URL export.');
    }
  } catch (uiError) {
    console.log('Chyba v UI interakci:', uiError.message);
  }

  const cookies = await driver.manage().getCookies();
  const cookieStr = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
  const exportUrl = `https://www.mobilmajak.cz/admin/sklady/doklady/polozky?type%5B0%5D=sklad-prijemka&date_range%5Bfrom%5D=${dateISO}&date_range%5Bto%5D=${dateISO}&item=bazar&list-type=stock-item-list&_export=xlsx`;
  const filePath = path.join(downloadDir, `vykupy_${dateISO}_${dateISO}.xlsx`);

  await downloadFileWithAxios(exportUrl, cookieStr, filePath);

  const workbook = XLSX.readFile(filePath);
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });
  if (rows.length <= 1) {
    console.log(`Žádná data pro ${dateISO}.`);
    return 0;
  }

  console.log(`Počet řádků k obohacení: ${rows.length - 1}`);
  const headers = rows[0];
  headers.push('ID prodejny', 'ID prodejce');

  let matchCountStores = 0;
  let matchCountUsers = 0;
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (!row || row.length === 0) continue;
    const stredisko = (row[4] || '').toString().trim();
    const spravce = (row[7] || '').toString().trim();
    let storeId = storesMap[stredisko] || 0;
    let userId = usersMap[spravce] || 0;
    if (storeId === 0 && stredisko) {
      for (const [name, id] of Object.entries(storesMap)) {
        if (
          name.toLowerCase().includes(stredisko.toLowerCase())
          || stredisko.toLowerCase().includes(name.toLowerCase())
        ) {
          storeId = id;
          break;
        }
      }
    }
    if (storeId !== 0) matchCountStores++;
    if (userId !== 0) matchCountUsers++;
    row.push(storeId, userId);
  }
  console.log(`Párování: ${matchCountStores} prodejen, ${matchCountUsers} prodejců.`);

  const newSheet = XLSX.utils.aoa_to_sheet(rows);
  workbook.Sheets[workbook.SheetNames[0]] = newSheet;
  XLSX.writeFile(workbook, filePath);

  await createWebVykupyTable(connection);
  return insertDataToWebVykupy(connection, rows);
}

async function main() {
  await Actor.init();

  const downloadDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadDir)) fs.mkdirSync(downloadDir, { recursive: true });

  const options = new chrome.Options();
  options.addArguments(
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
  );
  options.addArguments('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36');
  options.addArguments('--window-size=1920,1080');
  if (process.env.HEADLESS !== '0') {
    options.addArguments('--headless=new');
  }
  options.setUserPreferences({
    'download.default_directory': downloadDir,
    'download.prompt_for_download': false,
    'download.directory_upgrade': true,
  });

  const targetDates = resolveTargetDates();
  let driver;
  let connection;
  let totalInserted = 0;

  try {
    driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
    await driver.executeScript("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});");

    console.log('1. Přihlašuji se do systému...');
    await loginSymplio(driver);

    connection = await connectToMySQL();
    const usersMap = await getUsersMap(connection);
    const storesMap = await getStoresMap(connection);

    for (const dateISO of targetDates) {
      totalInserted += await processDay(driver, connection, usersMap, storesMap, dateISO, downloadDir);
    }

    console.log(`✅ Hotovo. Celkem vloženo ${totalInserted} nových řádků.`);
  } catch (err) {
    console.error('❌ Kritická chyba:', err);
    throw err;
  } finally {
    if (connection) await connection.end();
    if (driver) await driver.quit();
    await Actor.exit();
  }
}

async function createWebVykupyTable(connection) {
  const createTableSQL = `
    CREATE TABLE IF NOT EXISTS WEB_VYKUPY (
      id INT AUTO_INCREMENT PRIMARY KEY,
      Vystaveno DATE,
      Vystaveno_cas VARCHAR(20),
      Kod VARCHAR(100),
      Nazev TEXT,
      Stredisko VARCHAR(100),
      Pocet_kusu INT,
      Cena_ks_bez_DPH DECIMAL(10,2),
      Spravce VARCHAR(100),
      Kategorie VARCHAR(255),
      ID_PRODEJNY INT,
      ID_PRODEJCE INT,
      datum_vlozeni TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_vystaveno (Vystaveno),
      INDEX idx_stredisko (Stredisko),
      INDEX idx_spravce (Spravce),
      UNIQUE KEY unique_record (Vystaveno, Vystaveno_cas, Kod, Stredisko, Spravce)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `;
  await connection.execute(createTableSQL);
}

function convertExcelDate(excelDate) {
  if (!excelDate) return null;
  try {
    if (typeof excelDate === 'string') {
      const clean = excelDate.trim();
      const czechMatch = clean.match(/^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})/);
      if (czechMatch) {
        return `${czechMatch[3]}-${czechMatch[2].padStart(2, '0')}-${czechMatch[1].padStart(2, '0')}`;
      }
      const date = new Date(excelDate);
      if (!Number.isNaN(date.getTime())) return formatDateISO(date);
      return excelDate;
    }
    if (typeof excelDate === 'number') {
      const excelEpoch = new Date(1900, 0, 1);
      return formatDateISO(new Date(excelEpoch.getTime() + (excelDate - 2) * 24 * 60 * 60 * 1000));
    }
    return null;
  } catch (_) {
    return null;
  }
}

async function insertDataToWebVykupy(connection, rows) {
  let minDate = null;
  let maxDate = null;
  for (let i = 1; i < rows.length; i++) {
    const d = convertExcelDate(rows[i][0]);
    if (d) {
      if (!minDate || d < minDate) minDate = d;
      if (!maxDate || d > maxDate) maxDate = d;
    }
  }
  if (!minDate) {
    console.log('Žádná data k uložení.');
    return 0;
  }

  console.log(`Rozsah dat v souboru: ${minDate} - ${maxDate}`);
  const [existing] = await connection.execute(
    'SELECT Vystaveno, Vystaveno_cas, Kod, Stredisko, Spravce FROM WEB_VYKUPY WHERE Vystaveno BETWEEN ? AND ?',
    [minDate, maxDate],
  );
  const existingSet = new Set();
  existing.forEach((r) => {
    const dateStr = r.Vystaveno instanceof Date ? formatDateISO(r.Vystaveno) : r.Vystaveno;
    existingSet.add(`${dateStr}_${r.Vystaveno_cas}_${r.Kod}_${r.Stredisko}_${r.Spravce}`);
  });

  const insertSQL = `
    INSERT INTO WEB_VYKUPY (
      Vystaveno, Vystaveno_cas, Kod, Nazev, Stredisko,
      Pocet_kusu, Cena_ks_bez_DPH, Spravce, Kategorie,
      ID_PRODEJNY, ID_PRODEJCE
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `;

  let insertedCount = 0;
  let skippedCount = 0;
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (!row || row.length === 0) continue;
    const vystaveno = convertExcelDate(row[0]);
    const cas = (row[1] || '').toString();
    const kod = (row[2] || '').toString();
    const stredisko = (row[4] || '').toString();
    const spravce = (row[7] || '').toString();
    const key = `${vystaveno}_${cas}_${kod}_${stredisko}_${spravce}`;
    if (existingSet.has(key)) {
      skippedCount++;
      continue;
    }
    const values = [
      vystaveno,
      cas,
      kod,
      (row[3] || '').toString(),
      stredisko,
      parseInt(row[5], 10) || 0,
      parseFloat(row[6]) || 0,
      spravce,
      (row[8] || '').toString(),
      parseInt(row[9], 10) || null,
      parseInt(row[10], 10) || null,
    ];
    try {
      await connection.execute(insertSQL, values);
      insertedCount++;
    } catch (insertError) {
      if (insertError.code === 'ER_DUP_ENTRY' || insertError.message.includes('Duplicate entry')) {
        skippedCount++;
      } else {
        throw insertError;
      }
    }
  }
  console.log(`DB Update: Vloženo ${insertedCount} nových řádků. Přeskočeno ${skippedCount} duplicit.`);
  return insertedCount;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
