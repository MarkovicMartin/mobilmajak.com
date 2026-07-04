#!/usr/bin/env node
/**
 * Historický backfill: Symplio XLSX → processDownloadedTable → DELETE dní + INSERT.
 *
 *   node backfill-historical.js --from 2026-04-01 --to 2026-04-30 --file reports/symplio_....xlsx
 *   node backfill-historical.js --from 2026-05-01 --to 2026-05-31 --download
 *   PRODEJE_TABLE=WEB_PRODEJE_ALL_SHADOW node backfill-historical.js ...
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const {
  connectToMySQL,
  loadTechniciMapFromDb,
  loadProdejciMapFromDb,
  processDownloadedTable,
  insertDataToWebProdejeAll,
  createWebProdejeAllTable,
  getProdejeTableName,
} = require('./main.js');

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

async function main() {
  if (!process.env.DB_PASSWORD && !process.env.MYSQL_PASSWORD) {
    throw new Error('Nastav DB_PASSWORD pro připojení k MySQL');
  }

  const args = parseArgs(process.argv);
  const xlsxPath = resolveXlsxPath(args);
  if (!fs.existsSync(xlsxPath)) throw new Error(`XLSX neexistuje: ${xlsxPath}`);

  const table = getProdejeTableName();
  console.log(`Backfill ${args.from} .. ${args.to} → ${table}`);
  console.log(`Soubor: ${xlsxPath} (${fs.statSync(xlsxPath).size} B)`);

  const connection = await connectToMySQL();
  try {
    const techniciMap = await loadTechniciMapFromDb(connection);
    const prodejciMap = await loadProdejciMapFromDb(connection);
    const processed = await processDownloadedTable(xlsxPath, techniciMap, prodejciMap);
    console.log(`Zpracováno ${processed.rows.length} řádků z exportu`);

    if (args.dryRun) {
      console.log('DRY-RUN: zápis do DB přeskočen');
      return;
    }

    await createWebProdejeAllTable(connection);
    const inserted = await insertDataToWebProdejeAll(connection, processed.headers, processed.rows);
    console.log(`Backfill dokončen: vloženo ${inserted} řádků do ${table}`);
  } finally {
    await connection.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
