const { Actor } = require('apify');
const { Builder, By, until } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const XLSX = require('xlsx');
const { google } = require('googleapis');
const mysql = require('mysql2/promise');
const { loadSymplioCredentials } = require('./symplio-credentials');

// Pomocná funkce pro čekání
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Pomocná funkce pro převod Excel data na MySQL formát
function convertExcelDate(excelDate) {
    if (!excelDate) return null;
    
    try {
        // Pokud je to už string ve formátu DD.MM.YYYY nebo podobném
        if (typeof excelDate === 'string') {
            // Nejdříve odstranit všechny mezery z řetězce
            const cleanDate = excelDate.replace(/\s+/g, '');
            
            // Formát DD.MM.YYYY (bez mezer i s mezerami)
            const czechDateMatch = cleanDate.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
            if (czechDateMatch) {
                const [, day, month, year] = czechDateMatch;
                return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            }
            
            // Zkusit také původní string pro jiné formáty
            const czechDateWithSpaces = excelDate.match(/^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})$/);
            if (czechDateWithSpaces) {
                const [, day, month, year] = czechDateWithSpaces;
                return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            }
            
            // Formát YYYY-MM-DD (už správný)
            const isoDateMatch = excelDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
            if (isoDateMatch) {
                return excelDate;
            }
            
            // Zkusit parsovat jako obecné datum
            const date = new Date(excelDate);
            if (!isNaN(date.getTime())) {
                return date.toISOString().split('T')[0]; // YYYY-MM-DD
            }
        }
        
        // Pokud je to číslo (Excel serial date)
        if (typeof excelDate === 'number') {
            // Excel ukládá data jako počet dní od 1. ledna 1900
            const excelEpoch = new Date(1900, 0, 1);
            const date = new Date(excelEpoch.getTime() + (excelDate - 2) * 24 * 60 * 60 * 1000);
            return date.toISOString().split('T')[0]; // YYYY-MM-DD
        }
        
        // Pokud je to Date objekt
        if (excelDate instanceof Date) {
            return excelDate.toISOString().split('T')[0]; // YYYY-MM-DD
        }
        
        console.warn(`Nepodařilo se převést datum: ${excelDate}`);
        return null;
        
    } catch (error) {
        console.warn(`Chyba při převodu data ${excelDate}:`, error.message);
        return null;
    }
}

function resolveMysqlPassword() {
    const password = process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD;
    if (!password) {
        throw new Error('MySQL: nastav DB_PASSWORD nebo MYSQL_PASSWORD');
    }
    return password;
}

// MySQL konfigurace (heslo pouze z env, lazy při připojení)
const MYSQL_CONFIG = {
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    get password() {
        return resolveMysqlPassword();
    },
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
    connectTimeout: 120000, // 2 minuty
    acquireTimeout: 120000, // 2 minuty
    timeout: 300000 // 5 minut pro dotazy
};

// Funkce pro připojení k MySQL databázi
async function connectToMySQL() {
    try {
        console.log('Připojuji se k MySQL databázi...');
        const connection = await mysql.createConnection(MYSQL_CONFIG);
        console.log('Úspěšně připojen k MySQL databázi');
        return connection;
    } catch (error) {
        console.error('Chyba při připojení k MySQL:', error.message);
        throw error;
    }
}

// Načte mapování technik_id → "Jméno Příjmení" z tabulky WEB_USERS
async function loadTechniciMapFromDb(connection) {
    try {
        const [rows] = await connection.execute(
            'SELECT technik_id, jmeno, prijmeni FROM WEB_USERS WHERE technik_id IS NOT NULL'
        );
        const map = {};
        for (const row of rows) {
            const jmeno = (row.jmeno || '').trim();
            const prijmeni = (row.prijmeni || '').trim();
            if (row.technik_id != null && (jmeno || prijmeni)) {
                map[Number(row.technik_id)] = [jmeno, prijmeni].filter(Boolean).join(' ');
            }
        }
        console.log(`Načteno ${Object.keys(map).length} techniků z WEB_USERS (technik_id → jméno)`);
        return map;
    } catch (error) {
        console.warn('Nepodařilo se načíst techniky z WEB_USERS, použije se prázdné mapování:', error.message);
        return {};
    }
}

// Načte mapování "Jméno Příjmení" → id (ID prodejce) z tabulky WEB_USERS
async function loadProdejciMapFromDb(connection) {
    try {
        const [rows] = await connection.execute(
            'SELECT id, jmeno, prijmeni FROM WEB_USERS'
        );
        const map = {};
        for (const row of rows) {
            const jmeno = (row.jmeno || '').trim();
            const prijmeni = (row.prijmeni || '').trim();
            const fullName = [jmeno, prijmeni].filter(Boolean).join(' ');
            if (row.id != null && fullName) {
                map[fullName] = Number(row.id);
            }
        }
        console.log(`Načteno ${Object.keys(map).length} prodejců z WEB_USERS (jméno → id)`);
        return map;
    } catch (error) {
        console.warn('Nepodařilo se načíst prodejce z WEB_USERS, použije se prázdné mapování:', error.message);
        return {};
    }
}

// Funkce pro vytvoření tabulky WEB_PRODEJE_ALL
async function createWebProdejeAllTable(connection) {
    try {
        console.log('Vytvářím/aktualizuji tabulku WEB_PRODEJE_ALL...');
        
        // Vytvořit tabulku pouze pokud neexistuje
        const createTableSQL = `
            CREATE TABLE IF NOT EXISTS WEB_PRODEJE_ALL (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Vystaveno DATE,
                Kod VARCHAR(100),
                Nazev TEXT,
                Doklad VARCHAR(100),
                Objednavka VARCHAR(100),
                Pokladna VARCHAR(100),
                Stredisko VARCHAR(100),
                Poznamka TEXT,
                Poznamka_zakaznika TEXT,
                Objednavku_zalozil VARCHAR(100),
                Pocet_kusu INT,
                Cena_ks_vcl_DPH DECIMAL(10,2),
                Cena_ks_bez_DPH DECIMAL(10,2),
                Skladova_cena_bez_DPH DECIMAL(10,2),
                Spravce VARCHAR(100),
                Kategorie_puvodni TEXT,
                Marketingovy_kanal VARCHAR(100),
                Dropshipping VARCHAR(10),
                ID_PRODEJCE INT,
                ID_PRODEJNY INT,
                ZISK DECIMAL(10,2),
                KATEGORIE VARCHAR(255),
                KATEGORIE_1 VARCHAR(255),
                KATEGORIE_2 VARCHAR(255),
                Technik VARCHAR(100),
                k_servisu VARCHAR(10),
                datum_vlozeni TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_stredisko (Stredisko),
                INDEX idx_spravce (Spravce),
                INDEX idx_vystaveno (Vystaveno),
                INDEX idx_kategorie (KATEGORIE),
                INDEX idx_technik (Technik),
                UNIQUE KEY unique_polozka (Vystaveno, Kod, Doklad)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        `;
        
        await connection.execute(createTableSQL);
        console.log('Tabulka WEB_PRODEJE_ALL byla úspěšně vytvořena nebo již existuje');
        
    } catch (error) {
        console.error('Chyba při vytváření tabulky WEB_PRODEJE_ALL:', error.message);
        throw error;
    }
}

// Funkce pro smazání všech dat z tabulky WEB_PRODEJE_ALL
async function clearWebProdejeAllTable(connection) {
    try {
        console.log('Mažu všechna data z tabulky WEB_PRODEJE_ALL...');
        await connection.execute('DELETE FROM WEB_PRODEJE_ALL');
        console.log('Všechna data z tabulky WEB_PRODEJE_ALL byla smazána');
    } catch (error) {
        console.error('Chyba při mazání dat z tabulky WEB_PRODEJE_ALL:', error.message);
        throw error;
    }
}

// Funkce pro nahrání dat do MySQL tabulky s chytrou logikou proti duplicitám
async function insertDataToMySQL(connection, headers, rows) {
    try {
        console.log('Nahrávám data do MySQL tabulky WEB_PRODEJE s kontrolou duplicit...');
        
        // Mapování sloupců z Excel na MySQL sloupce
        const columnMapping = {
            0: 'Vystaveno',
            1: 'Kod', 
            2: 'Nazev',
            3: 'Doklad',
            4: 'Nazev_dokladu',
            5: 'Objednavka',
            6: 'Polozka',
            7: 'Stredisko',
            8: 'Poznamka',
            9: 'Poznamka_dokladu',
            10: 'Pocet_kusu',
            11: 'Cena_ks_vcl_DPH',
            12: 'Skladova_cena_bez_DPH',
            13: 'Skladova_cena_bez_DPH_total',
            14: 'Spravce',
            15: 'Marketingovy_kanal',
            16: 'Dropshipping',
            17: 'ID_PRODEJCE',
            18: 'ID_PRODEJNY',
            19: 'ZISK',
            20: 'KATEGORIE',
            21: 'KATEGORIE_1',
            22: 'KATEGORIE_2'
        };
        
        // Získat aktuální datum pro kontrolu duplicit
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0]; // YYYY-MM-DD format
        
        console.log(`Kontroluji duplicity pro datum: ${todayStr}`);
        
        // Získat existující záznamy pro dnešní den
        const [existingRecords] = await connection.execute(
            'SELECT Doklad, Polozka, Stredisko, Spravce, Pocet_kusu, Cena_ks_vcl_DPH FROM WEB_PRODEJE WHERE Vystaveno = ?',
            [todayStr]
        );
        
        console.log(`Nalezeno ${existingRecords.length} existujících záznamů pro dnešní den`);
        
        // Vytvořit set pro rychlé vyhledávání duplicit
        const existingSet = new Set();
        existingRecords.forEach(record => {
            const key = `${record.Doklad}_${record.Polozka}_${record.Stredisko}_${record.Spravce}_${record.Pocet_kusu}_${record.Cena_ks_vcl_DPH}`;
            existingSet.add(key);
        });
        
        // Připravit SQL pro insert
        const insertSQL = `
            INSERT INTO WEB_PRODEJE (
                Vystaveno, Kod, Nazev, Doklad, Nazev_dokladu, Objednavka, Polozka, 
                Stredisko, Poznamka, Poznamka_dokladu, Pocet_kusu, Cena_ks_vcl_DPH,
                Skladova_cena_bez_DPH, Skladova_cena_bez_DPH_total, Spravce, 
                Marketingovy_kanal, Dropshipping, ID_PRODEJCE, ID_PRODEJNY, ZISK,
                KATEGORIE, KATEGORIE_1, KATEGORIE_2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        
        // Připravit statement pro batch insert
        let insertedCount = 0;
        let skippedCount = 0;
        const batchSize = 100;
        
        for (let i = 0; i < rows.length; i += batchSize) {
            const batch = rows.slice(i, i + batchSize);
            
            for (const row of batch) {
                if (!row || row.length === 0) continue;
                
                // Vytvořit klíč pro kontrolu duplicit
                const doklad = row[3] || '';
                const polozka = row[6] || '';
                const stredisko = row[7] || '';
                const spravce = row[14] || '';
                const pocetKusu = parseInt(row[10]) || 0;
                const cenaKs = parseFloat(row[11]) || 0;
                
                const duplicateKey = `${doklad}_${polozka}_${stredisko}_${spravce}_${pocetKusu}_${cenaKs}`;
                
                // Kontrola, zda záznam již existuje
                if (existingSet.has(duplicateKey)) {
                    skippedCount++;
                    continue; // Přeskočit tento záznam
                }
                
                // Převést řádek na hodnoty pro MySQL
                const convertedDate = convertExcelDate(row[0]);
                
                // Debug výpis pro prvních 5 řádků
                if (insertedCount < 5) {
                    console.log(`DEBUG řádek ${insertedCount + 1}: Původní datum: "${row[0]}" (${typeof row[0]}) → Převedeno: "${convertedDate}"`);
                }
                
                const values = [
                    convertedDate,  // Vystaveno - konverze Excel data
                    row[1] || null,  // Kod
                    row[2] || null,  // Nazev
                    row[3] || null,  // Doklad
                    row[4] || null,  // Nazev_dokladu
                    row[5] || null,  // Objednavka
                    row[6] || null,  // Polozka
                    row[7] || null,  // Stredisko
                    row[8] || null,  // Poznamka
                    row[9] || null,  // Poznamka_dokladu
                    parseInt(row[10]) || 0,  // Pocet_kusu
                    parseFloat(row[11]) || 0,  // Cena_ks_vcl_DPH
                    parseFloat(row[12]) || 0,  // Skladova_cena_bez_DPH
                    parseFloat(row[13]) || 0,  // Skladova_cena_bez_DPH_total
                    row[14] || null,  // Spravce
                    row[15] || null,  // Marketingovy_kanal
                    row[16] || null,  // Dropshipping
                    parseInt(row[17]) || null,  // ID_PRODEJCE
                    parseInt(row[18]) || null,  // ID_PRODEJNY
                    parseFloat(row[19]) || 0,  // ZISK
                    row[20] || null,  // KATEGORIE
                    row[21] || null,  // KATEGORIE_1
                    row[22] || null   // KATEGORIE_2
                ];
                
                await connection.execute(insertSQL, values);
                insertedCount++;
            }
            
            console.log(`Zpracováno ${Math.min(i + batchSize, rows.length)} z ${rows.length} řádků...`);
        }
        
        console.log(`Úspěšně nahráno ${insertedCount} nových řádků do tabulky WEB_PRODEJE`);
        console.log(`Přeskočeno ${skippedCount} duplicitních záznamů`);
        
        // Statistiky
        const [countResult] = await connection.execute('SELECT COUNT(*) as total FROM WEB_PRODEJE');
        console.log(`Celkový počet řádků v tabulce: ${countResult[0].total}`);
        
        return insertedCount;
        
    } catch (error) {
        console.error('Chyba při nahrávání dat do MySQL:', error.message);
        throw error;
    }
}

function getProdejeTableName() {
    return process.env.PRODEJE_TABLE || 'WEB_PRODEJE_ALL';
}

function buildLineImportKey(date, cas, kod, doklad, cena, seqOnDoklad) {
    return `${date}|${cas || ''}|${kod || ''}|${doklad || ''}|${cena}|${seqOnDoklad}`;
}

/** Poznamka_dokladu neplníme z exportu položek – doplňuje sync-doklad-notes.js (seznam dokladů). */
async function loadPreservedDokladNotes(connection, table, dates) {
    if (!dates.length) return new Map();
    const placeholders = dates.map(() => '?').join(', ');
    const [rows] = await connection.execute(
        `SELECT Doklad, MAX(Poznamka_dokladu) AS note
         FROM ${table}
         WHERE Vystaveno IN (${placeholders})
           AND Poznamka_dokladu IS NOT NULL
           AND TRIM(Poznamka_dokladu) <> ''
         GROUP BY Doklad`,
        dates,
    );
    const map = new Map();
    for (const row of rows) {
        if (row.Doklad && row.note) map.set(String(row.Doklad).trim(), String(row.note).trim());
    }
    return map;
}

// Funkce pro nahrání dat do tabulky WEB_PRODEJE_ALL (vše najednou)
async function insertDataToWebProdejeAll(connection, headers, rows) {
    try {
        const TABLE = getProdejeTableName();
        console.log(`Nahrávám data do MySQL tabulky ${TABLE} (jeden řádek Symplia = jeden INSERT)...`);
        const startTime = new Date();
        console.log(`[${startTime.toLocaleTimeString()}] Začátek nahrávání dat do databáze`);

        const [countBefore] = await connection.execute(`SELECT COUNT(*) as count FROM ${TABLE}`);
        const existingCount = countBefore[0].count;
        console.log(`Počet existujících záznamů v databázi: ${existingCount}`);

        const C = {};
        headers.forEach((h, i) => { if (h) C[h.toString().trim()] = i; });
        console.log('Mapa sloupců pro INSERT:', JSON.stringify(C));

        const uniqueDates = new Set();
        for (const row of rows) {
            if (!row || row.length === 0) continue;
            const g = (name) => { const idx = C[name]; return idx !== undefined ? row[idx] : null; };
            const d = convertExcelDate(g('Vystaveno'));
            if (d) uniqueDates.add(d);
        }
        console.log(`Dny k re-importu (DELETE + INSERT): ${[...uniqueDates].join(', ')}`);

        const dateList = [...uniqueDates];
        const preservedDokladNotes = await loadPreservedDokladNotes(connection, TABLE, dateList);
        if (preservedDokladNotes.size > 0) {
            console.log(`Zachováno Poznamka_dokladu z DB pro ${preservedDokladNotes.size} dokladů (sync-doklad-notes)`);
        }

        if (uniqueDates.size > 0) {
            const placeholders = [...uniqueDates].map(() => '?').join(', ');
            const [delResult] = await connection.execute(
                `DELETE FROM ${TABLE} WHERE Vystaveno IN (${placeholders})`,
                [...uniqueDates]
            );
            console.log(`Smazáno ${delResult.affectedRows} řádků pro tyto dny před novým importem`);
        }

        const insertSQL = `
            INSERT INTO ${TABLE} (
                Vystaveno, cas_prodeje, Kod, Nazev, Doklad, Objednavka, Pokladna,
                Stredisko, Poznamka, Poznamka_dokladu, Poznamka_zakaznika, Objednavku_zalozil,
                Pocet_kusu, Cena_ks_vcl_DPH, Cena_ks_bez_DPH, Skladova_cena_bez_DPH,
                Spravce, Kategorie_puvodni, Marketingovy_kanal, Dropshipping,
                ID_PRODEJCE, ID_PRODEJNY, ZISK, KATEGORIE, KATEGORIE_1, KATEGORIE_2,
                Technik, k_servisu
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;

        let insertedCount = 0;
        let skippedExactInFile = 0;
        let withPreservedPoznamkaDokladu = 0;
        const seqPerDoklad = new Map();
        const seenInFile = new Set();
        const batchSize = 100;

        console.log(`Celkem řádků k vložení: ${rows.length}`);

        for (let i = 0; i < rows.length; i += batchSize) {
            const batch = rows.slice(i, i + batchSize);

            for (const row of batch) {
                if (!row || row.length === 0) continue;

                const g = (name) => { const idx = C[name]; return idx !== undefined ? row[idx] : null; };
                const convertedDate = convertExcelDate(g('Vystaveno'));
                const casStr = g('Vystaveno (čas)') || '';
                const kodStr = g('Kód') || '';
                const dokladStr = g('Doklad') || '';
                const cenaVal = parseFloat(g('Cena ks vč. DPH')) || 0;

                const dokladSeqKey = `${convertedDate}|${dokladStr}`;
                const seqOnDoklad = (seqPerDoklad.get(dokladSeqKey) || 0) + 1;
                seqPerDoklad.set(dokladSeqKey, seqOnDoklad);

                const lineKey = buildLineImportKey(convertedDate, casStr, kodStr, dokladStr, cenaVal, seqOnDoklad);
                if (seenInFile.has(lineKey)) {
                    skippedExactInFile++;
                    continue;
                }
                seenInFile.add(lineKey);

                if (insertedCount < 3) {
                    console.log(`DEBUG řádek ${insertedCount + 1}: Datum: "${g('Vystaveno')}" → "${convertedDate}", Čas: "${casStr}", Kód: "${kodStr}"`);
                    console.log(`DEBUG řádek ${insertedCount + 1}: Technik: "${g('Technik')}", k_servisu: "${g('k_servisu')}"`);
                }

                const poznamkaDokladu = preservedDokladNotes.get(dokladStr) || null;
                if (poznamkaDokladu) withPreservedPoznamkaDokladu++;

                const values = [
                    convertedDate,
                    casStr || null,
                    kodStr || null,
                    g('Název') || null,
                    dokladStr || null,
                    g('Objednávka') || null,
                    g('Pokladna') || null,
                    g('Středisko') || null,
                    g('Poznámka') || null,
                    poznamkaDokladu,
                    g('Poznámka zákazníka') || null,
                    g('Objednávku založil') || null,
                    parseInt(g('Počet kusů')) || 0,
                    cenaVal,
                    parseFloat(g('Cena ks bez DPH')) || 0,
                    parseFloat(g('Skladová cena bez DPH')) || 0,
                    g('Správce') || null,
                    g('Kategorie') || null,
                    g('Marketingový kanál') || null,
                    g('Dropshipping') || null,
                    parseInt(g('ID PRODEJCE')) || null,
                    parseInt(g('ID PRODEJNY')) || null,
                    parseFloat(g('ZISK')) || 0,
                    g('KATEGORIE') || null,
                    g('KATEGORIE_1') || null,
                    g('KATEGORIE_2') || null,
                    g('Technik') || null,
                    g('k_servisu') || null
                ];

                await connection.execute(insertSQL, values);
                insertedCount++;
            }

            const processed = Math.min(i + batchSize, rows.length);
            const percentage = ((processed / rows.length) * 100).toFixed(1);
            console.log(`Zpracováno ${processed} z ${rows.length} řádků... (${percentage}%)`);

            if (processed % Math.floor(rows.length / 10) === 0 || processed === rows.length) {
                console.log(`[${new Date().toLocaleTimeString()}] Progress: ${percentage}% - ${processed}/${rows.length} řádků`);
            }
        }

        // Zjistit finální počet záznamů
        const [countAfter] = await connection.execute(`SELECT COUNT(*) as count FROM ${TABLE}`);
        const newCount = countAfter[0].count;

        const endTime = new Date();
        const duration = Math.round((endTime - startTime) / 1000);

        console.log(`[${endTime.toLocaleTimeString()}] Konec nahrávání dat do databáze`);
        console.log(`Celková doba zpracování: ${duration} sekund (${Math.round(duration/60)} minut)`);
        console.log(`Bylo zpracováno ${rows.length} řádků z exportu`);
        console.log(`Vloženo záznamů: ${insertedCount}`);
        console.log(`Řádků se zachovanou Poznamka_dokladu (z sync-doklad-notes): ${withPreservedPoznamkaDokladu}`);
        console.log(`Přeskočeno přesných duplicit v jednom souboru: ${skippedExactInFile}`);
        console.log(`Celkový počet řádků v tabulce ${TABLE}: ${newCount}`);

        return insertedCount;

    } catch (error) {
        console.error('Chyba při nahrávání dat do WEB_PRODEJE_ALL:', error.message);
        throw error;
    }
}

async function sendDataToWebhook(data, webhookUrl = 'https://script.google.com/macros/s/AKfycbwVFjNWYHiBa4QmOQ5CJAgTNdKYaaVZSgTxNGLnZ9GEQpn_SCIqlfkBn2cWvG7n71pP/exec') {
    console.log('Odesílám data na Google Apps Script:', webhookUrl);
    try {
        // Vytvoření českého formátu data a času
        const now = new Date();
        const options = { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            timeZone: 'Europe/Prague'
        };
        const czechDateTime = now.toLocaleString('cs-CZ', options);
        
        const response = await axios({
            method: 'POST',
            url: webhookUrl,
            headers: {
                'Content-Type': 'application/json'
            },
            data: {
                action: 'updateSheet',
                timestamp: czechDateTime,
                headers: data.headers,
                rows: data.rows,
                targetSpreadsheetId: '1t3v7I_HwbPkMdmJjNEcDN1dFDoAvood7FVyoK_PBTNE',
                sheetName: 'List 1'
            }
        });
        
        console.log('Odpověď z Google Apps Script:', response.data);
        return { success: true, response: response.data };
    } catch (error) {
        console.error('Chyba při odesílání dat na Google Apps Script:', error.message);
        if (error.response) {
            console.error('Status:', error.response.status);
            console.error('Data:', error.response.data);
        }
        return { success: false, error: error.message, details: error.response?.data };
    }
}

// Funkce pro přímé stahování souboru pomocí axios
async function downloadFileWithAxios(url, cookies, outputPath) {
    console.log(`Stahování souboru z URL: ${url}`);
    try {
        const response = await axios({
            method: 'GET',
            url: url,
            responseType: 'arraybuffer',
            headers: {
                Cookie: cookies,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
            }
        });
        
        fs.writeFileSync(outputPath, response.data);
        console.log(`Soubor úspěšně stažen do: ${outputPath}`);
        return true;
    } catch (error) {
        console.error('Chyba při přímém stahování souboru:', error.message);
        if (error.response) {
            console.error('Status:', error.response.status);
            console.error('Headers:', JSON.stringify(error.response.headers));
        }
        return false;
    }
}

// Funkce pro vytvoření listu "prodejny" s agregovanými údaji
function createProdejnySheet(processedRows, headers) {
    console.log('Vytvářím list "prodejny" s agregovanými údaji...');
    
    // Najít indexy potřebných sloupců
    const getColumnIndex = (columnName) => {
        const index = headers.findIndex(header => 
            header && header.toString().toLowerCase().includes(columnName.toLowerCase())
        );
        return index !== -1 ? index : null;
    };
    
    // Sestavit přesnou mapu názvů → indexů z předaných hlaviček
    const cMap = {};
    headers.forEach((h, i) => { if (h) cMap[h.toString().trim()] = i; });

    const strediskoIndex = getColumnIndex('Středisko');
    const marketingovyKanalIndex = getColumnIndex('Marketingový kanál');
    const idProdejnyIndex = cMap['ID PRODEJNY'] ?? null;
    const cenaIndex = getColumnIndex('Cena ks vč. DPH');
    const skladovaIndex = getColumnIndex('Skladová');
    const ziskIndex = cMap['ZISK'] ?? null;
    const kategorieIndex = cMap['KATEGORIE'] ?? null;
    const kategorie1Index = cMap['KATEGORIE_1'] ?? null;
    
    console.log('Indexy sloupců pro prodejny list:', {
        stredisko: strediskoIndex,
        marketingovyKanal: marketingovyKanalIndex,
        idProdejny: idProdejnyIndex,
        cena: cenaIndex,
        skladova: skladovaIndex,
        zisk: ziskIndex,
        kategorie: kategorieIndex
    });
    
    // Agregační struktura podle prodejen a eshopu
    const prodejnyMap = new Map();
    
    // Najít poslední datum z tabulky
    const dnesDatum = new Date().toLocaleDateString('cs-CZ');
    
    // Mapování ID prodejen (včetně ESHOP)
    const prodejnyIdMap = {
        'Globus': 1,
        'Čepkov': 3,
        'Šternberk': 6,
        'Vsetín': 5,
        'Přerov': 4,
        'Hlavní sklad - Senimo': 2,
        'ESHOP': 7
    };
    
    // Projít všechny řádky a agregovat údaje
    for (const row of processedRows) {
        if (!row || row.length === 0) continue;
        
        const stredisko = row[strediskoIndex] ? row[strediskoIndex].toString().trim() : null;
        const marketingovyKanal = row[marketingovyKanalIndex] ? row[marketingovyKanalIndex].toString().trim().toLowerCase() : '';
        const cena = parseFloat(row[cenaIndex]) || 0;
        const skladova = parseFloat(row[skladovaIndex]) || 0;
        const zisk = parseFloat(row[ziskIndex]) || 0;
        const kategorie = row[kategorieIndex] ? row[kategorieIndex].toString().trim() : '';
        const kategorie1 = kategorie1Index !== null && row[kategorie1Index] ? row[kategorie1Index].toString().trim() : '';
        
        // Určit, zda jde o ESHOP nebo PRODEJNU
        let nazevProdejny;
        let idProdejny;
        
        if (marketingovyKanal === 'e-shop') {
            // ESHOP kanál
            nazevProdejny = 'ESHOP';
            idProdejny = 7;
        } else {
            // PRODEJNA (všechny ostatní kanály)
            nazevProdejny = stredisko;
            idProdejny = prodejnyIdMap[stredisko] || null;
        }
        
        if (!nazevProdejny) continue;
        
        // Inicializace prodejny/eshopu v mapě
        if (!prodejnyMap.has(nazevProdejny)) {
            prodejnyMap.set(nazevProdejny, {
                prodejna: nazevProdejny,
                idProdejny: idProdejny,
                celkemObrat: 0,
                celkemNaklad: 0,
                celkemZisk: 0,
                bazarTelefonyObrat: 0,
                bazarTelefonyNaklad: 0,
                bazarTelefonyZisk: 0,
                prislusenstviObrat: 0,
                prislusenstviZisk: 0,
                noveTelefonyObrat: 0,
                noveTelefonyZisk: 0,
                sluzbyObrat: 0
            });
        }
        
        const prodejnaData = prodejnyMap.get(nazevProdejny);
        
        // Přičíst celkové hodnoty
        prodejnaData.celkemObrat += cena;
        prodejnaData.celkemNaklad += skladova;
        prodejnaData.celkemZisk += zisk;
        
        // Zkontrolovat, zda patří do BAZAR_TELEFONY kategorií
        const bazarKategorie = ['!Výkup bazaru', 'POUŽITÉ TELEFONY', 'Kaufland'];
        if (bazarKategorie.some(kat => kategorie.includes(kat))) {
            prodejnaData.bazarTelefonyObrat += cena;
            prodejnaData.bazarTelefonyNaklad += skladova;
            prodejnaData.bazarTelefonyZisk += zisk;
        }
        
        // Zkontrolovat, zda patří do PŘÍSLUŠENSTVÍ kategorie
        if (kategorie.includes('PŘÍSLUŠENSTVÍ')) {
            prodejnaData.prislusenstviObrat += cena;
            prodejnaData.prislusenstviZisk += zisk;
        }
        
        // Zkontrolovat, zda patří do NOVÉ TELEFONY kategorie
        if (kategorie.includes('NOVÉ TELEFONY')) {
            prodejnaData.noveTelefonyObrat += cena;
            prodejnaData.noveTelefonyZisk += zisk;
        }
        
        // Zkontrolovat, zda patří do SLUŽBY kategorie (filtrovat podle KATEGORIE_1)
        if (kategorie1.includes('Služby')) {
            prodejnaData.sluzbyObrat += cena;
        }
    }
    
    // Vytvoření hlaviček pro list prodejny
    const prodejnyHeaders = [
        'DATUM',
        'PRODEJNA', 
        'ID PRODEJNY',
        'CELKEM_OBRAT',
        'CELKEM_NAKLAD',
        'CELKEM_ZISK',
        'BAZAR_TELEFONY_OBRAT',
        'BAZAR_TELEFONY_NAKLAD',
        'BAZAR_TELEFONY_ZISK',
        'PŘÍSLUŠENSTVÍ_OBRAT',
        'PŘÍSLUŠENSTVÍ_ZISK',
        'NOVÉ_TELEFONY_OBRAT',
        'NOVÉ_TELEFONY_ZISK',
        'SLUŽBY_OBRAT'
    ];
    
    // Vytvoření řádků pro každou prodejnu (ESHOP na konec)
    const prodejnyRows = [];
    let eshopData = null;
    
    // Nejdříve přidat všechny prodejny kromě ESHOP
    for (const [prodejna, data] of prodejnyMap) {
        if (prodejna === 'ESHOP') {
            eshopData = data;
            continue;
        }
        
        prodejnyRows.push([
            dnesDatum,
            data.prodejna,
            data.idProdejny,
            Math.round(data.celkemObrat * 100) / 100, // Zaokrouhlení na 2 desetinná místa
            Math.round(data.celkemNaklad * 100) / 100,
            Math.round(data.celkemZisk * 100) / 100,
            Math.round(data.bazarTelefonyObrat * 100) / 100,
            Math.round(data.bazarTelefonyNaklad * 100) / 100,
            Math.round(data.bazarTelefonyZisk * 100) / 100,
            Math.round(data.prislusenstviObrat * 100) / 100,
            Math.round(data.prislusenstviZisk * 100) / 100,
            Math.round(data.noveTelefonyObrat * 100) / 100,
            Math.round(data.noveTelefonyZisk * 100) / 100,
            Math.round(data.sluzbyObrat * 100) / 100
        ]);
    }
    
    // Přidat ESHOP na konec, pokud existuje
    if (eshopData) {
        prodejnyRows.push([
            dnesDatum,
            eshopData.prodejna,
            eshopData.idProdejny,
            Math.round(eshopData.celkemObrat * 100) / 100,
            Math.round(eshopData.celkemNaklad * 100) / 100,
            Math.round(eshopData.celkemZisk * 100) / 100,
            Math.round(eshopData.bazarTelefonyObrat * 100) / 100,
            Math.round(eshopData.bazarTelefonyNaklad * 100) / 100,
            Math.round(eshopData.bazarTelefonyZisk * 100) / 100,
            Math.round(eshopData.prislusenstviObrat * 100) / 100,
            Math.round(eshopData.prislusenstviZisk * 100) / 100,
            Math.round(eshopData.noveTelefonyObrat * 100) / 100,
            Math.round(eshopData.noveTelefonyZisk * 100) / 100,
            Math.round(eshopData.sluzbyObrat * 100) / 100
        ]);
    }
    
    console.log(`Vytvořen list prodejny s ${prodejnyRows.length} prodejnami`);
    
    // Debug - finální kontrola agregace
    for (const [prodejna, data] of prodejnyMap) {
        console.log(`FINÁLNÍ: ${prodejna} | BAZAR: ${data.bazarTelefonyObrat}/${data.bazarTelefonyZisk} | PŘÍSLUŠENSTVÍ: ${data.prislusenstviObrat}/${data.prislusenstviZisk} | NOVÉ TEL: ${data.noveTelefonyObrat}/${data.noveTelefonyZisk} | SLUŽBY: ${data.sluzbyObrat}`);
    }
    
    return [prodejnyHeaders, ...prodejnyRows];
}

// Funkce pro zpracování stažené tabulky s přidáním nových sloupců
// techniciMap: { technik_id: 'Jméno Příjmení' } z WEB_USERS
// prodejciMap: { 'Jméno Příjmení': id } z WEB_USERS
async function processDownloadedTable(filePath, techniciMap = {}, prodejciMap = {}) {
    console.log('Zpracovávám staženou tabulku...');
    
    try {
        // Načtení Excel souboru
        const workbook = XLSX.readFile(filePath);
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        
        // Převedení na JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        
        if (jsonData.length < 2) {
            throw new Error('Tabulka neobsahuje dostatek dat');
        }
        
        // Získání hlaviček (první řádek)
        const headers = jsonData[0];
        console.log('Hlavičky tabulky:', headers);
        
        // Mapování prodejců (prodejciMap předáno z DB - WEB_USERS)
        // Mapování servisních techniků (techniciMap předáno z DB - WEB_USERS)
        
        // Mapování prodejen podle střediska
        const prodejnyMap = {
            'Globus': 1,
            'Čepkov': 3,
            'Šternberk': 6,
            'Vsetín': 5,
            'Přerov': 4,
            'Hlavní sklad - Senimo': 2
        };
        
        // Najít indexy sloupců
        const getColumnIndex = (columnName) => {
            const index = headers.findIndex(header => 
                header && header.toString().toLowerCase().includes(columnName.toLowerCase())
            );
            if (index === -1) {
                console.warn(`Sloupec '${columnName}' nebyl nalezen`);
                return null;
            }
            return index;
        };
        
        const spravceIndex = getColumnIndex('Správce');
        const strediskoIndex = getColumnIndex('Středisko');
        const cenaIndex = getColumnIndex('Cena ks bez DPH');
        const skladovaCenaIndex = getColumnIndex('Skladová cena bez DPH');
        const pocetKusuIndex = getColumnIndex('Počet kusů');
        const kategorieIndex = getColumnIndex('Kategorie');
        
        console.log('Indexy sloupců:', {
            spravce: spravceIndex,
            stredisko: strediskoIndex,
            cena: cenaIndex,
            skladovaCena: skladovaCenaIndex,
            pocetKusu: pocetKusuIndex,
            kategorie: kategorieIndex
        });
        
        // Sestavit mapu Excel sloupců podle názvů (robustní, nezávislé na pořadí)
        const excelColMap = {};
        headers.forEach((h, i) => { if (h) excelColMap[h.toString().trim()] = i; });
        const numExcelCols = headers.length;
        console.log(`Počet sloupců v Excelu: ${numExcelCols}`);
        console.log('Excel colMap:', JSON.stringify(excelColMap));

        // Přidání vypočtených sloupců dynamicky na konec hlaviček
        const newHeaders = [...headers];
        newHeaders.push('ID PRODEJCE');   // numExcelCols + 0
        newHeaders.push('ID PRODEJNY');   // numExcelCols + 1
        newHeaders.push('ZISK');          // numExcelCols + 2
        newHeaders.push('KATEGORIE');     // numExcelCols + 3
        newHeaders.push('KATEGORIE_1');   // numExcelCols + 4
        newHeaders.push('KATEGORIE_2');   // numExcelCols + 5
        newHeaders.push('Technik');       // numExcelCols + 6
        newHeaders.push('k_servisu');     // numExcelCols + 7

        console.log(`Celkový počet sloupců po přidání computed: ${newHeaders.length}`);
        
        // Zpracování datových řádků
        const processedRows = [];
        
        for (let i = 1; i < jsonData.length; i++) {
            const row = jsonData[i];
            if (row.length === 0) continue;
            
            const newRow = [...row];

            // Rozšíř řádek pro vypočtené sloupce (dynamicky dle počtu Excel sloupců)
            while (newRow.length < numExcelCols + 8) {
                newRow.push(null);
            }

            // ID PRODEJCE
            let idProdejce = null;
            if (spravceIndex !== null && row[spravceIndex]) {
                const spravceName = row[spravceIndex].toString().trim();
                idProdejce = prodejciMap[spravceName] || null;
            }
            newRow[numExcelCols + 0] = idProdejce;

            // ID PRODEJNY
            let idProdejny = null;
            if (strediskoIndex !== null && row[strediskoIndex]) {
                const strediskoName = row[strediskoIndex].toString().trim();
                idProdejny = prodejnyMap[strediskoName] || null;
            }
            newRow[numExcelCols + 1] = idProdejny;

            // ZISK
            let zisk = null;
            if (cenaIndex !== null && skladovaCenaIndex !== null && pocetKusuIndex !== null) {
                const cena = parseFloat(row[cenaIndex]) || 0;
                const skladovaCena = parseFloat(row[skladovaCenaIndex]) || 0;
                const pocetKusu = parseInt(row[pocetKusuIndex]) || 0;
                
                zisk = (cena - skladovaCena) * pocetKusu;
            }
            newRow[numExcelCols + 2] = zisk;

            // KATEGORIE, KATEGORIE_1, KATEGORIE_2
            let kategorie = null;
            let kategorie1 = null;
            let kategorie2 = null;
            
            if (kategorieIndex !== null && row[kategorieIndex]) {
                const kategorieString = row[kategorieIndex].toString().trim();
                // Rozdělení kategorie podle " / "
                const kategorieParts = kategorieString.split(' / ').map(part => part.trim()).filter(part => part);
                
                // Přiřazení prvních tří částí
                if (kategorieParts.length > 0) {
                    kategorie = kategorieParts[0];
                }
                if (kategorieParts.length > 1) {
                    kategorie1 = kategorieParts[1];
                }
                if (kategorieParts.length > 2) {
                    kategorie2 = kategorieParts[2];
                }
            }
            
            newRow[numExcelCols + 3] = kategorie;
            newRow[numExcelCols + 4] = kategorie1;
            newRow[numExcelCols + 5] = kategorie2;
            
            // Technik (index 24) a k_servisu (index 25)
            let technikId = null;
            let kServisu = null;
            
            // Dynamické indexy sloupců dle mapy (nezávislé na pořadí)
            const poznamkaZakaznikaIndex = excelColMap['Poznámka zákazníka'] ?? 9;
            const kodIndex = excelColMap['Kód'] ?? 2;
            
            if (poznamkaZakaznikaIndex < row.length && row[poznamkaZakaznikaIndex]) {
                const poznamkaZakaznika = row[poznamkaZakaznikaIndex].toString().trim();
                
                // Pokud je poznámka neprázdná, nastavíme k_servisu na "ANO"
                if (poznamkaZakaznika) {
                    kServisu = 'ANO';
                    
                    // Pokusíme se najít ID technika v poznámce
                    // Vzor: Data: { [P10409 => 102], }
                    const dataMatch = poznamkaZakaznika.match(/Data:\s*\{\s*([^}]+)\s*\}/);
                    if (dataMatch) {
                        const dataContent = dataMatch[1];
                        // Rozdělíme podle čárek pro více položek
                        const items = dataContent.split(',').map(item => item.trim());
                        
                        // Aktuální kód položky z řádku
                        const currentKod = kodIndex < row.length && row[kodIndex] ? row[kodIndex].toString().trim() : '';
                        
                        if (currentKod) {
                            // Hledáme položku, která odpovídá aktuálnímu kódu
                            for (const item of items) {
                                // Vzor: [P10409 => 102]
                                const itemMatch = item.match(/\[([^=>\s]+)\s*=>\s*(\d+)\]/);
                                if (itemMatch) {
                                    const itemKod = itemMatch[1].trim();
                                    const itemTechnikId = itemMatch[2].trim();
                                    
                                    // Pokud se kód shoduje s aktuálním řádkem
                                    if (itemKod === currentKod) {
                                        const parsedTechnikId = parseInt(itemTechnikId);
                                        // Převedeme ID technika na jméno pomocí mapování
                                        technikId = techniciMap[parsedTechnikId] || `ID: ${parsedTechnikId}`;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            newRow[numExcelCols + 6] = technikId;
            newRow[numExcelCols + 7] = kServisu;

            // Debug výpis pro kontrolu (pouze pro první 3 řádky)
            if (i <= 3) {
                console.log(`DEBUG - Řádek ${i}:`);
                console.log(`  Délka řádku: ${newRow.length}, Excel sloupců: ${numExcelCols}`);
                console.log(`  Kód [${excelColMap['Kód']}]: ${row[excelColMap['Kód']]}`);
                console.log(`  ID PRODEJCE [${numExcelCols + 0}]: ${newRow[numExcelCols + 0]}`);
                console.log(`  ID PRODEJNY [${numExcelCols + 1}]: ${newRow[numExcelCols + 1]}`);
                console.log(`  ZISK [${numExcelCols + 2}]: ${newRow[numExcelCols + 2]}`);
                console.log(`  KATEGORIE [${numExcelCols + 3}]: ${newRow[numExcelCols + 3]}`);
                console.log(`  Technik [${numExcelCols + 6}]: ${newRow[numExcelCols + 6]}`);
                console.log(`  k_servisu [${numExcelCols + 7}]: ${newRow[numExcelCols + 7]}`);
                console.log(`  Poznámka zákazníka [${poznamkaZakaznikaIndex}]: "${row[poznamkaZakaznikaIndex] || ''}"`);
                console.log(`  Kód položky [${kodIndex}]: "${row[kodIndex] || ''}"`);
            }
            
            processedRows.push(newRow);
        }
        
        // Vytvoření nového workbooku
        const newWorkbook = XLSX.utils.book_new();
        const newWorksheet = XLSX.utils.aoa_to_sheet([newHeaders, ...processedRows]);
        
        // Nastavení šířky sloupců pro hlavní list
        const mainCols = newHeaders.map(header => {
            const headerLength = header ? header.toString().length : 10;
            return { wch: Math.max(headerLength + 2, 12) }; // Minimum 12 znaků, nebo délka hlavičky + 2
        });
        newWorksheet['!cols'] = mainCols;
        
        XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'Zpracované data');
        
        // Vytvoření listu "prodejny" s agregovanými údaji
        const prodejnyData = createProdejnySheet(processedRows, newHeaders);
        const prodejnyWorksheet = XLSX.utils.aoa_to_sheet(prodejnyData);
        
        // Nastavení šířky sloupců pro list prodejny
        const prodejnyHeaders = prodejnyData[0];
        const prodejnyCols = prodejnyHeaders.map(header => {
            const headerLength = header ? header.toString().length : 10;
            return { wch: Math.max(headerLength + 2, 15) }; // Minimum 15 znaků pro prodejny list
        });
        prodejnyWorksheet['!cols'] = prodejnyCols;
        
        XLSX.utils.book_append_sheet(newWorkbook, prodejnyWorksheet, 'prodejny');
        
        // Uložení zpracované tabulky do složky vysledek
        const outputPath = path.join(__dirname, '..', 'vysledek', 'zpracovane_polozky.xlsx');
        XLSX.writeFile(newWorkbook, outputPath);
        
        console.log(`Zpracovaná tabulka uložena do: ${outputPath}`);
        
        // Převod na CSV pro uložení do složky vysledek
        const csvData = [newHeaders, ...processedRows];
        const csvContent = csvData.map(row => 
            row.map(cell => 
                typeof cell === 'string' ? `"${cell.replace(/"/g, '""')}"` : cell
            ).join(',')
        ).join('\n');
        
        const csvPath = path.join(__dirname, '..', 'vysledek', 'zpracovane_polozky.csv');
        fs.writeFileSync(csvPath, csvContent);
        
        console.log(`CSV soubor uložen do: ${csvPath}`);
        
        return {
            xlsxPath: outputPath,
            csvPath: csvPath,
            headers: newHeaders,
            rows: processedRows
        };
        
    } catch (error) {
        console.error('Chyba při zpracování tabulky:', error.message);
        throw error;
    }
}

// Funkce pro zpracování WAF výzvy
async function handleWafChallenge(driver) {
    try {
        // Kontrola, zda je na stránce WAF výzva
        const wafElements = await driver.findElements(By.css('body'));
        const pageText = await driver.getPageSource();
        
        if (pageText.includes('WAF') || pageText.includes('Cloudflare') || pageText.includes('DDoS')) {
            console.log('Detekována WAF výzva, čekám...');
            await sleep(5000);
        }
    } catch (error) {
        console.log('Chyba při kontrole WAF:', error.message);
    }
}

// Hlavní funkce
async function main() {
    // Inicializace Apify
    await Actor.init();
    
    // Vytvoření adresáře pro stahování
    const downloadDir = '/tmp/downloads';
    if (!fs.existsSync(downloadDir)) {
        fs.mkdirSync(downloadDir, { recursive: true });
    }
    
    // Vytvoření adresáře pro zpracované soubory
    const processedDir = '/tmp/processed';
    if (!fs.existsSync(processedDir)) {
        fs.mkdirSync(processedDir, { recursive: true });
    }
    
    // Nastavení Chrome driveru s parametry pro obcházení detekce robotů
    const options = new chrome.Options();
    options.addArguments('--no-sandbox');
    options.addArguments('--disable-dev-shm-usage');
    // options.addArguments('--headless'); // Vypnuto pro ladění
    options.addArguments('--disable-gpu');
    options.addArguments('--disable-blink-features=AutomationControlled');
    options.addArguments('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36');
    options.addArguments('--window-size=1920,1080');

    // Headless režim řízený proměnnou prostředí (výchozí: zapnuto na serveru)
    const headlessEnv = process.env.HEADLESS;
    const shouldRunHeadless = headlessEnv === undefined ? true : headlessEnv !== '0';
    if (shouldRunHeadless) {
        // Nový headless mód pro moderní Chrome
        options.addArguments('--headless=new');
    }

    // Volitelné nastavení binárky Chromu přes env proměnnou (např. CHROME_BIN=/usr/bin/google-chrome)
    if (process.env.CHROME_BIN) {
        try {
            options.setChromeBinaryPath(process.env.CHROME_BIN);
            console.log(`Používám Chrome binary z: ${process.env.CHROME_BIN}`);
        } catch (e) {
            console.log('Nelze nastavit CHROME_BIN:', e.message);
        }
    }
    
    // Nastavení proxy - pokud je k dispozici
    const input = await Actor.getInput();
    if (input && input.proxy) {
        console.log('Používám proxy server:', input.proxy);
        options.addArguments(`--proxy-server=${input.proxy}`);
    }
    
    // Nastavení preferencí pro stahování
    const prefs = {
        'download.default_directory': downloadDir,
        'download.prompt_for_download': false,
        'download.directory_upgrade': true,
        'safebrowsing.enabled': true,
        'profile.default_content_setting_values.notifications': 2,
        'credentials_enable_service': false,
        'profile.password_manager_enabled': false
    };
    options.setUserPreferences(prefs);
    
    let driver;
    try {
        // Nastavení ChromeDriveru pro lokální spuštění na macOS
        let service;
        try {
            // Pokusíme se najít chromedriver v PATH
            service = new chrome.ServiceBuilder();
        } catch (e) {
            console.log('ChromeDriver není v PATH, zkusíme bez explicit service...');
            service = null;
        }
        
        const builder = new Builder()
            .forBrowser('chrome')
            .setChromeOptions(options);
            
        if (service) {
            builder.setChromeService(service);
        }
        
        driver = await builder.build();
        
        // Nastavení extra hlaviček pro requesty
        await driver.executeScript(`
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        `);
        
        // 1. Přihlášení
        console.log('1. Přihlašuji se do systému...');
        await driver.get('https://www.mobilmajak.cz/admin');
        
        // Kontrola WAF výzvy
        await handleWafChallenge(driver);
        
        // Počkat na zobrazení přihlašovacího formuláře
        await driver.wait(until.elementLocated(By.name('_username')), 30000);

        const symplio = loadSymplioCredentials();
        await driver.findElement(By.name('_username')).sendKeys(symplio.user);
        await driver.findElement(By.name('_password')).sendKeys(symplio.pass);
        await driver.findElement(By.xpath("//button[@type='submit' and contains(., 'Přihlásit')]")).click();
        
        // Počkat a zkontrolovat WAF
        await sleep(3000);
        await handleWafChallenge(driver);
        
        // Počkat na přihlášení a zobrazení stránky
        await driver.wait(until.elementLocated(By.xpath("//a[contains(@class, 'btn-primary') and contains(., 'Globus')]")), 30000);
        
        // Kliknutí na Globus
        await driver.findElement(By.xpath("//a[contains(@class, 'btn-primary') and contains(., 'Globus')]")).click();
        
        // Počkat na načtení stránky po kliknutí na Globus
        await sleep(3000);
        
        // Kontrola WAF výzvy
        await handleWafChallenge(driver);
        
        // 2. Přejít na stránku položek
        console.log('2. Přecházím na stránku položek...');
        await driver.get('https://www.mobilmajak.cz/admin/doklady/polozky');
        
        // Kontrola WAF výzvy
        await handleWafChallenge(driver);
        
        // Počkat na načtení stránky s položkami
        await sleep(5000);
        console.log('Na stránce položek - hledám formulář s filtrem data');
        
        // 3. Nastavení období na pouze dnešní den
        console.log('3. Nastavuji období na pouze dnešní den...');
        const today = new Date();
        
        const dateFromStr = today.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
        const dateToStr = today.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
        
        console.log(`Období: od ${dateFromStr} do ${dateToStr} (pouze dnešní den)`);
        
        try {
            // Hledáme formulář pro filtrování
            const filterForm = await driver.wait(
                until.elementLocated(By.css('form')), 
                10000
            );
            console.log('Formulář nalezen');
            
            // Najdeme pole pro datum od
            let dateFromInput = null;
            let dateToInput = null;
            
            try {
                dateFromInput = await driver.findElement(By.id('date_range_from'));
                dateToInput = await driver.findElement(By.id('date_range_to'));
                console.log('Nalezena datumová pole by ID');
            } catch (e) {
                console.log('Nenalezena datumová pole by ID:', e.message);
                
                // Zkusíme najít pole podle name
                try {
                    dateFromInput = await driver.findElement(By.name('date_range_from'));
                    dateToInput = await driver.findElement(By.name('date_range_to'));
                    console.log('Nalezena datumová pole by NAME');
                } catch (e2) {
                    console.log('Nenalezena datumová pole by NAME:', e2.message);
                    
                    // Zkusíme najít pole typu date
                    try {
                        const dateInputs = await driver.findElements(By.css("input[type='date']"));
                        if (dateInputs.length >= 2) {
                            dateFromInput = dateInputs[0];
                            dateToInput = dateInputs[1];
                            console.log('Nalezena datumová pole pomocí typu date');
                        }
                    } catch (e3) {
                        console.log('Nenalezena datumová pole typu date:', e3.message);
                    }
                }
            }
            
            if (dateFromInput && dateToInput) {
                // Vyplníme datum od
                await dateFromInput.clear();
                await dateFromInput.sendKeys(dateFromStr);
                console.log(`Datum od ${dateFromStr} zadáno`);
                
                // Vyplníme datum do
                await dateToInput.clear();
                await dateToInput.sendKeys(dateToStr);
                console.log(`Datum do ${dateToStr} zadáno`);
                
                // 4. Stisknutí tlačítka filtrovat
                console.log('4. Stiskám tlačítko filtrovat...');
                let filterButton = null;
                try {
                    filterButton = await driver.findElement(
                        By.xpath("//button[contains(@class, 'btn-primary') and contains(normalize-space(), 'Filtrovat')]")
                    );
                    console.log('Nalezeno tlačítko Filtrovat podle třídy a textu');
                } catch (e) {
                    console.log('Nenalezeno tlačítko Filtrovat podle třídy a textu:', e.message);
                    
                    // Zkusíme najít tlačítko podle textu
                    try {
                        filterButton = await driver.findElement(
                            By.xpath("//button[contains(normalize-space(), 'Filtrovat')]")
                        );
                        console.log('Nalezeno tlačítko Filtrovat jen podle textu');
                    } catch (e2) {
                        console.log('Nenalezeno tlačítko Filtrovat jen podle textu:', e2.message);
                        
                        // Zkusíme najít jakékoliv tlačítko ve formuláři
                        try {
                            filterButton = await filterForm.findElement(By.css('button[type="submit"]'));
                            console.log('Nalezeno tlačítko submit ve formuláři');
                        } catch (e3) {
                            console.log('Nenalezeno tlačítko submit ve formuláři:', e3.message);
                        }
                    }
                }
                
                if (filterButton) {
                    await filterButton.click();
                    console.log('Kliknuto na tlačítko filtrování');
                    
                    // Počkat na výsledky filtru
                    await sleep(3000);
                    
                    // 5. Stáhnout tabulku
                    console.log('5. Stahuji tabulku...');
                    try {
                        console.log('Používám přímé HTTP stahování pro export XLSX...');
                        
                        // Získáme cookies ze stránky
                        const cookies = await driver.manage().getCookies();
                        const cookieString = cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
                        console.log('Získány cookies pro autentizaci');
                        
                        // Vytvoříme URL pro export
                        const baseUrl = 'https://www.mobilmajak.cz';
                        const exportUrl = `${baseUrl}/admin/doklady/polozky?type%5B0%5D=faktura-faktura&type%5B1%5D=faktura-storno&type%5B2%5D=faktura-dobropis&type%5B3%5D=uctenka-uctenka&type%5B4%5D=uctenka-storno&type%5B5%5D=uctenka-dobropis&type%5B6%5D=buctenka-buctenka&type%5B7%5D=buctenka-storno&type%5B8%5D=buctenka-dobropis&date_range%5Bfrom%5D=${dateFromStr.split('.').reverse().join('-')}&date_range%5Bto%5D=${dateToStr.split('.').reverse().join('-')}&list-type=invoice-list&_export=xlsx`;
                        
                        console.log('Exportní URL:', exportUrl);
                        
                        // Nastavíme cestu pro stažený soubor
                        const outputPath = path.join(downloadDir, 'polozky.xlsx');
                        
                        // Stáhneme soubor přímo pomocí HTTP requestu
                        const downloadSuccess = await downloadFileWithAxios(exportUrl, cookieString, outputPath);
                        
                        if (downloadSuccess) {
                            console.log('Soubor položek úspěšně stažen přímým HTTP požadavkem');
                            
                            // 6. Připojení k MySQL, načtení mapování techniků z WEB_USERS, zpracování tabulky a nahrání dat
                            let mysqlConnection = null;
                            try {
                                mysqlConnection = await connectToMySQL();
                                const techniciMap = await loadTechniciMapFromDb(mysqlConnection);
                                const prodejciMap = await loadProdejciMapFromDb(mysqlConnection);
                                
                                console.log('6. Zpracovávám tabulku s přidáním nových sloupců...');
                                const processedData = await processDownloadedTable(outputPath, techniciMap, prodejciMap);
                                
                                console.log('Zpracovaný soubor byl uložen do složky vysledek');
                                
                                // 7. Nahrání dat do MySQL databáze (tabulka WEB_PRODEJE_ALL)
                                console.log('7. Nahrávám data do MySQL databáze WEB_PRODEJE_ALL...');
                                await createWebProdejeAllTable(mysqlConnection);
                                const insertedRows = await insertDataToWebProdejeAll(mysqlConnection, processedData.headers, processedData.rows);
                                console.log(`MySQL: Úspěšně nahráno ${insertedRows} řádků do tabulky WEB_PRODEJE_ALL`);
                                console.log('Soubory k dispozici:');
                                console.log(`- Excel: ${processedData.xlsxPath}`);
                                console.log(`- CSV: ${processedData.csvPath}`);
                            } catch (mysqlError) {
                                console.error('Chyba při práci s MySQL:', mysqlError.message);
                            } finally {
                                if (mysqlConnection) {
                                    await mysqlConnection.end();
                                    console.log('MySQL připojení ukončeno');
                                }
                            }

                            // Smazat stažený soubor
                            fs.unlinkSync(outputPath);
                        } else {
                            console.log('Nepodařilo se stáhnout soubor položek přímým HTTP požadavkem');
                        }
                    } catch (e) {
                        console.log('Chyba při stahování XLSX souboru:', e.message);
                    }
                    
                    // Počkat pro stabilitu
                    await sleep(3000);
                }
            } else {
                console.log('Nepodařilo se najít pole pro datum');
            }
        } catch (err) {
            console.log('Chyba při hledání formuláře nebo datumových polí:', err.message);
        }
        
        // Nahrání informací o průběhu do datasetu
        const dataset = await Actor.openDataset();
        await dataset.pushData({
            message: 'Zpracování dokončeno pro celý letošní rok do včerejška',
            date_from: dateFromStr,
            date_to: dateToStr,
            output_files: {
                zpracovane_polozky: 'zpracovane_polozky.xlsx'
            },
            status: 'success',
            note: 'Data nahrávána s kontrolou duplicit - pouze nové záznamy'
        });
        
                    console.log('Celý proces dokončen. Data byla zpracována pro dnešní den a přidána do databáze (bez duplicit).');
        
    } catch (error) {
        console.error('Chyba při běhu aktoru:', error);
        // Nahrát chybu do datasetu
        const dataset = await Actor.openDataset();
        await dataset.pushData({
            message: 'Chyba při běhu aktoru',
            error: error.message,
            stack: error.stack
        });
        throw error;
    } finally {
        if (driver) {
            await driver.quit();
        }
        // Ukončení Apify
        await Actor.exit();
    }
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = {
    connectToMySQL,
    loadTechniciMapFromDb,
    loadProdejciMapFromDb,
    processDownloadedTable,
    insertDataToWebProdejeAll,
    createWebProdejeAllTable,
    buildLineImportKey,
    getProdejeTableName,
    convertExcelDate,
    MYSQL_CONFIG,
};