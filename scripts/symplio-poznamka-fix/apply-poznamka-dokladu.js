#!/usr/bin/env node
/**
 * Doplní Poznamka_dokladu v WEB_PRODEJE_ALL z mapy doklad → poznámka (bez re-importu položek).
 */
const mysql = require('mysql2/promise');

const TABLE = process.env.PRODEJE_TABLE || 'WEB_PRODEJE_ALL';

function resolveMysqlPassword() {
  const password = process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD;
  if (!password) {
    throw new Error('MySQL: nastav DB_PASSWORD nebo MYSQL_PASSWORD');
  }
  return password;
}

function getMysqlConfig() {
  return {
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    get password() {
      return resolveMysqlPassword();
    },
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
    connectTimeout: 120000,
  };
}

async function connectToMySQL() {
  return mysql.createConnection(getMysqlConfig());
}

function trimNote(value) {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text || null;
}

/**
 * @param {import('mysql2/promise').Connection} connection
 * @param {Record<string, string>} map doklad → poznámka
 * @param {{ dateFrom: string, dateTo: string, dryRun?: boolean }} options ISO dates YYYY-MM-DD
 */
async function applyPoznamkaDokladuMap(connection, map, options) {
  const { dateFrom, dateTo, dryRun = false } = options;
  const entries = Object.entries(map).filter(([, note]) => trimNote(note));
  let dokladyTouched = 0;
  let rowsUpdated = 0;
  let rowsSkipped = 0;

  for (const [doklad, noteRaw] of entries) {
    const note = trimNote(noteRaw);
    if (!note) continue;

    const [existing] = await connection.execute(
      `SELECT COUNT(*) AS cnt FROM ${TABLE}
       WHERE Doklad = ? AND Vystaveno >= ? AND Vystaveno <= ?
         AND COALESCE(Poznamka_dokladu, '') = ?`,
      [doklad, dateFrom, dateTo, note],
    );
    const alreadyOk = Number(existing[0]?.cnt || 0);
    const [allRows] = await connection.execute(
      `SELECT COUNT(*) AS cnt FROM ${TABLE}
       WHERE Doklad = ? AND Vystaveno >= ? AND Vystaveno <= ?`,
      [doklad, dateFrom, dateTo],
    );
    const rowCount = Number(allRows[0]?.cnt || 0);
    if (rowCount === 0) continue;

    if (alreadyOk === rowCount) {
      rowsSkipped += rowCount;
      continue;
    }

    dokladyTouched += 1;
    if (dryRun) {
      rowsUpdated += rowCount - alreadyOk;
      continue;
    }

    const [result] = await connection.execute(
      `UPDATE ${TABLE}
       SET Poznamka_dokladu = ?
       WHERE Doklad = ? AND Vystaveno >= ? AND Vystaveno <= ?
         AND COALESCE(Poznamka_dokladu, '') <> ?`,
      [note, doklad, dateFrom, dateTo, note],
    );
    rowsUpdated += result.affectedRows || 0;
  }

  return { dokladyTouched, rowsUpdated, rowsSkipped, mapSize: entries.length };
}

module.exports = {
  TABLE,
  connectToMySQL,
  applyPoznamkaDokladuMap,
};

if (require.main === module) {
  const fs = require('fs');
  const path = require('path');

  function parseArgs(argv) {
    const out = { json: null, from: null, to: null, dryRun: false };
    for (let i = 2; i < argv.length; i++) {
      const a = argv[i];
      if (a === '--json') out.json = argv[++i];
      else if (a === '--from') out.from = argv[++i];
      else if (a === '--to') out.to = argv[++i];
      else if (a === '--dry-run') out.dryRun = true;
    }
    if (!out.json || !out.from || !out.to) {
      throw new Error('Použití: node apply-poznamka-dokladu.js --json map.json --from YYYY-MM-DD --to YYYY-MM-DD');
    }
    return out;
  }

  (async () => {
    const args = parseArgs(process.argv);
    const raw = JSON.parse(fs.readFileSync(path.resolve(args.json), 'utf8'));
    const map = raw.map || raw;
    const connection = await connectToMySQL();
    try {
      const stats = await applyPoznamkaDokladuMap(connection, map, {
        dateFrom: args.from,
        dateTo: args.to,
        dryRun: args.dryRun,
      });
      console.log(JSON.stringify(stats, null, 2));
    } finally {
      await connection.end();
    }
  })().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
