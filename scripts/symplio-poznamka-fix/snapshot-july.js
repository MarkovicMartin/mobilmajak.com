#!/usr/bin/env node
/**
 * Záloha řádků WEB_PRODEJE_ALL za červenec (pro rollback / diff po backfillu poznámek).
 *
 *   node snapshot-july.js --year 2026 --month 7 --out reports/snapshot_2026-07_before.json
 */
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

function parseArgs(argv) {
  const out = { year: 2026, month: 7 };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--year') out.year = parseInt(argv[++i], 10);
    else if (a === '--month') out.month = parseInt(argv[++i], 10);
    else if (a === '--out') out.out = argv[++i];
  }
  const pad = (n) => String(n).padStart(2, '0');
  if (!out.out) {
    out.out = path.join(__dirname, 'reports', `snapshot_${out.year}-${pad(out.month)}_before.json`);
  }
  out.from = `${out.year}-${pad(out.month)}-01`;
  const lastDay = new Date(out.year, out.month, 0).getDate();
  out.to = `${out.year}-${pad(out.month)}-${pad(lastDay)}`;
  return out;
}

async function main() {
  if (!process.env.DB_PASSWORD && !process.env.MYSQL_PASSWORD) {
    throw new Error('Nastav DB_PASSWORD');
  }
  const args = parseArgs(process.argv);
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    password: process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD,
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
  });

  try {
    const [rows] = await connection.execute(
      `SELECT id, Vystaveno, cas_prodeje, Kod, Nazev, Doklad, Objednavka, Pokladna, Stredisko,
              Poznamka, Poznamka_dokladu, Poznamka_zakaznika, Pocet_kusu, Cena_ks_vcl_DPH,
              Spravce, ID_PRODEJCE, ID_PRODEJNY
       FROM WEB_PRODEJE_ALL
       WHERE Vystaveno >= ? AND Vystaveno <= ?
       ORDER BY Vystaveno, Doklad, id`,
      [args.from, args.to],
    );

    const doklady = new Set(rows.map((r) => r.Doklad).filter(Boolean));
    const withNote = rows.filter(
      (r) =>
        (r.Poznamka && String(r.Poznamka).trim()) ||
        (r.Poznamka_dokladu && String(r.Poznamka_dokladu).trim()) ||
        (r.Poznamka_zakaznika && String(r.Poznamka_zakaznika).trim()),
    );

    const payload = {
      created_at: new Date().toISOString(),
      period: { from: args.from, to: args.to },
      row_count: rows.length,
      doklad_count: doklady.size,
      rows_with_any_note: withNote.length,
      doklady_with_poznamka_dokladu: [
        ...new Set(
          rows
            .filter((r) => r.Poznamka_dokladu && String(r.Poznamka_dokladu).trim())
            .map((r) => r.Doklad),
        ),
      ],
      rows,
    };

    fs.mkdirSync(path.dirname(args.out), { recursive: true });
    fs.writeFileSync(args.out, JSON.stringify(payload, null, 2));
    console.log(`Snapshot: ${args.out}`);
    console.log(`  řádků: ${payload.row_count}, dokladů: ${payload.doklad_count}`);
    console.log(`  řádků s poznámkou: ${payload.rows_with_any_note}`);
    console.log(`  dokladů s Poznamka_dokladu: ${payload.doklady_with_poznamka_dokladu.length}`);
  } finally {
    await connection.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
