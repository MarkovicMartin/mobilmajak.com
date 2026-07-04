#!/usr/bin/env node
/**
 * Obnoví řádky WEB_PRODEJE_ALL ze snapshotu (jen poznámky nebo celé řádky).
 *
 *   node restore-from-snapshot.js --file reports/snapshot_2026-07_before.json --dry-run
 *   node restore-from-snapshot.js --file reports/snapshot_2026-07_before.json
 */
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

function parseArgs(argv) {
  const out = { dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--file') out.file = argv[++i];
    else if (a === '--dry-run') out.dryRun = true;
  }
  if (!out.file) throw new Error('Chybí --file');
  if (!path.isAbsolute(out.file)) out.file = path.join(__dirname, out.file);
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  const snapshot = JSON.parse(fs.readFileSync(args.file, 'utf8'));
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    password: process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD,
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
  });

  try {
    const { from, to } = snapshot.period;
    console.log(`Rollback období ${from} – ${to}, řádků ve snapshotu: ${snapshot.row_count}`);
    if (args.dryRun) {
      console.log('DRY-RUN – bez zápisu');
      return;
    }

    await connection.beginTransaction();
    const [del] = await connection.execute(
      'DELETE FROM WEB_PRODEJE_ALL WHERE Vystaveno >= ? AND Vystaveno <= ?',
      [from, to],
    );
    console.log(`Smazáno ${del.affectedRows} řádků`);

    const insertSQL = `
      INSERT INTO WEB_PRODEJE_ALL (
        id, Vystaveno, cas_prodeje, Kod, Nazev, Doklad, Objednavka, Pokladna, Stredisko,
        Poznamka, Poznamka_dokladu, Poznamka_zakaznika, Pocet_kusu, Cena_ks_vcl_DPH,
        Spravce, ID_PRODEJCE, ID_PRODEJNY
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    for (const row of snapshot.rows) {
      await connection.execute(insertSQL, [
        row.id,
        row.Vystaveno,
        row.cas_prodeje,
        row.Kod,
        row.Nazev,
        row.Doklad,
        row.Objednavka,
        row.Pokladna,
        row.Stredisko,
        row.Poznamka,
        row.Poznamka_dokladu,
        row.Poznamka_zakaznika,
        row.Pocet_kusu,
        row.Cena_ks_vcl_DPH,
        row.Spravce,
        row.ID_PRODEJCE,
        row.ID_PRODEJNY,
      ]);
    }
    await connection.commit();
    console.log(`Obnoveno ${snapshot.rows.length} řádků ze snapshotu`);
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    await connection.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
