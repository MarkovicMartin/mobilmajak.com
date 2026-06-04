#!/usr/bin/env node
/**
 * Bezpečný import do WEB_PRODEJE_ALL:
 * - žádné DELETE / UPDATE / ALTER / CREATE TABLE
 * - pouze INSERT řádků s Vystaveno < 2024-01-01
 * - při jakémkoli řádku >= cutoff → okamžité ukončení (ochrana existujících dat)
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const {
  connectToMySQL,
  loadTechniciMapFromDb,
  loadProdejciMapFromDb,
  processDownloadedTable,
  buildLineImportKey,
  convertExcelDate,
} = require('./main.js');

const TABLE = 'WEB_PRODEJE_ALL';
const CUTOFF_DATE = process.env.BACKFILL_CUTOFF_DATE || '2024-01-01';

function parseArgs(argv) {
  const out = { download: false, dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--download') out.download = true;
    else if (a === '--dry-run') out.dryRun = true;
    else if (a === '--from') out.from = argv[++i];
    else if (a === '--to') out.to = argv[++i];
    else if (a === '--file') out.file = argv[++i];
    else if (a === '--out') out.out = argv[++i];
  }
  if (!out.from || !out.to) throw new Error('Chybí --from a --to (YYYY-MM-DD)');
  return out;
}

function resolveXlsxPath(args) {
  const reportsDir = args.out || path.join(__dirname, 'reports');
  fs.mkdirSync(reportsDir, { recursive: true });

  if (args.download || !args.file) {
    const xlsxPath = path.join(reportsDir, `symplio_${args.from}_${args.to}.xlsx`);
    console.log(`Stahuji Symplio export ${args.from} .. ${args.to} (compare.js)...`);
    const r = spawnSync(
      process.execPath,
      [
        path.join(__dirname, 'compare.js'),
        '--from',
        args.from,
        '--to',
        args.to,
        '--download',
        '--out',
        reportsDir,
      ],
      { stdio: 'inherit', cwd: __dirname, env: process.env },
    );
    if (r.status !== 0) throw new Error('compare.js --download selhal');
    return xlsxPath;
  }

  let p = args.file;
  if (!path.isAbsolute(p)) p = path.join(__dirname, p);
  if (!fs.existsSync(p)) p = path.join(reportsDir, path.basename(args.file));
  return p;
}

async function monthAlreadyHasRows(connection, from, toExcl) {
  const [rows] = await connection.execute(
    `SELECT COUNT(*) AS n FROM ${TABLE} WHERE Vystaveno >= ? AND Vystaveno < ?`,
    [from, toExcl],
  );
  return Number(rows[0].n) > 0;
}

async function insertPre2024Only(connection, headers, rows) {
  const C = {};
  headers.forEach((h, i) => {
    if (h) C[h.toString().trim()] = i;
  });

  const insertSQL = `
    INSERT INTO ${TABLE} (
      Vystaveno, cas_prodeje, Kod, Nazev, Doklad, Objednavka, Pokladna,
      Stredisko, Poznamka, Poznamka_zakaznika, Objednavku_zalozil,
      Pocet_kusu, Cena_ks_vcl_DPH, Cena_ks_bez_DPH, Skladova_cena_bez_DPH,
      Spravce, Kategorie_puvodni, Marketingovy_kanal, Dropshipping,
      ID_PRODEJCE, ID_PRODEJNY, ZISK, KATEGORIE, KATEGORIE_1, KATEGORIE_2,
      Technik, k_servisu
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `;

  let insertedCount = 0;
  let skippedAfterCutoff = 0;
  let skippedExactInFile = 0;
  const seqPerDoklad = new Map();
  const seenInFile = new Set();
  const batchSize = 100;

  for (let i = 0; i < rows.length; i += batchSize) {
    const batch = rows.slice(i, i + batchSize);

    for (const row of batch) {
      if (!row || row.length === 0) continue;

      const g = (name) => {
        const idx = C[name];
        return idx !== undefined ? row[idx] : null;
      };
      const convertedDate = convertExcelDate(g('Vystaveno'));
      if (!convertedDate) continue;

      if (convertedDate >= CUTOFF_DATE) {
        throw new Error(
          `Ochrana dat: řádek s Vystaveno=${convertedDate} >= ${CUTOFF_DATE}. Import zastaven.`,
        );
      }

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
        g('Poznámka zákazníka') || null,
        g('Objednávku založil') || null,
        parseInt(g('Počet kusů'), 10) || 0,
        cenaVal,
        parseFloat(g('Cena ks bez DPH')) || 0,
        parseFloat(g('Skladová cena bez DPH')) || 0,
        g('Správce') || null,
        g('Kategorie') || null,
        g('Marketingový kanál') || null,
        g('Dropshipping') || null,
        parseInt(g('ID PRODEJCE'), 10) || null,
        parseInt(g('ID PRODEJNY'), 10) || null,
        parseFloat(g('ZISK')) || 0,
        g('KATEGORIE') || null,
        g('KATEGORIE_1') || null,
        g('KATEGORIE_2') || null,
        g('Technik') || null,
        g('k_servisu') || null,
      ];

      await connection.execute(insertSQL, values);
      insertedCount++;
    }
  }

  return { insertedCount, skippedExactInFile, skippedAfterCutoff };
}

async function main() {
  const args = parseArgs(process.argv);
  const toExcl = new Date(`${args.to}T12:00:00`);
  toExcl.setDate(toExcl.getDate() + 1);
  const toExclStr = toExcl.toISOString().slice(0, 10);

  if (args.from >= CUTOFF_DATE) {
    console.log(`Přeskočeno ${args.from}..${args.to}: období je od ${CUTOFF_DATE} (chráněná data).`);
    return;
  }

  const xlsxPath = resolveXlsxPath(args);
  if (!fs.existsSync(xlsxPath)) throw new Error(`XLSX neexistuje: ${xlsxPath}`);

  console.log(`[insert-only] ${args.from} .. ${args.to} → ${TABLE}, cutoff < ${CUTOFF_DATE}`);
  console.log(`Soubor: ${xlsxPath} (${fs.statSync(xlsxPath).size} B)`);

  const connection = await connectToMySQL();
  try {
    if (await monthAlreadyHasRows(connection, args.from, toExclStr)) {
      console.log(`Přeskočeno: v ${TABLE} už existují řádky pro ${args.from} .. ${args.to}`);
      return;
    }

    const techniciMap = await loadTechniciMapFromDb(connection);
    const prodejciMap = await loadProdejciMapFromDb(connection);
    const processed = await processDownloadedTable(xlsxPath, techniciMap, prodejciMap);
    console.log(`Zpracováno ${processed.rows.length} řádků z exportu`);

    if (args.dryRun) {
      console.log('DRY-RUN: zápis do DB přeskočen');
      return;
    }

    const [before] = await connection.execute(`SELECT COUNT(*) AS n FROM ${TABLE}`);
    const result = await insertPre2024Only(connection, processed.headers, processed.rows);
    const [after] = await connection.execute(`SELECT COUNT(*) AS n FROM ${TABLE}`);
    console.log(
      `Hotovo: +${result.insertedCount} řádků (tabulka ${before[0].n} → ${after[0].n}), duplicity v souboru ${result.skippedExactInFile}`,
    );
  } finally {
    await connection.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
