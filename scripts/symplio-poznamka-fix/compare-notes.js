#!/usr/bin/env node
/**
 * Porovnání snapshotu před backfillem vs. aktuální DB (jen poznámky + počty).
 *
 *   node compare-notes.js --before reports/snapshot_2026-07_before.json
 */
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--before') out.before = argv[++i];
  }
  if (!out.before) throw new Error('Chybí --before');
  if (!path.isAbsolute(out.before)) out.before = path.join(__dirname, out.before);
  return out;
}

function noteKey(row) {
  return [
    row.Poznamka || '',
    row.Poznamka_dokladu || '',
    row.Poznamka_zakaznika || '',
  ]
    .map((s) => String(s).trim())
    .join('|');
}

async function main() {
  const args = parseArgs(process.argv);
  const before = JSON.parse(fs.readFileSync(args.before, 'utf8'));
  const { from, to } = before.period;

  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || 'db.dw300.webglobe.com',
    user: process.env.DB_USER || 'multi_724223',
    password: process.env.DB_PASSWORD || process.env.MYSQL_PASSWORD,
    database: process.env.DB_NAME || 'multi_724223',
    charset: 'utf8mb4',
  });

  try {
    const [afterRows] = await connection.execute(
      `SELECT id, Vystaveno, Kod, Doklad, Poznamka, Poznamka_dokladu, Poznamka_zakaznika
       FROM WEB_PRODEJE_ALL WHERE Vystaveno >= ? AND Vystaveno <= ?
       ORDER BY Vystaveno, Doklad, id`,
      [from, to],
    );

    const beforeById = new Map(before.rows.map((r) => [r.id, r]));
    const afterById = new Map(afterRows.map((r) => [r.id, r]));

    let noteChanged = 0;
    let noteAdded = 0;
    const samples = [];

    for (const [id, a] of afterById) {
      const b = beforeById.get(id);
      if (!b) continue;
      const bn = noteKey(b);
      const an = noteKey(a);
      if (bn === an) continue;
      if (!bn && an) noteAdded++;
      else noteChanged++;
      if (samples.length < 30) {
        samples.push({
          id,
          doklad: a.Doklad,
          kod: a.Kod,
          before: { poznamka: b.Poznamka, poznamka_dokladu: b.Poznamka_dokladu, poznamka_zakaznika: b.Poznamka_zakaznika },
          after: { poznamka: a.Poznamka, poznamka_dokladu: a.Poznamka_dokladu, poznamka_zakaznika: a.Poznamka_zakaznika },
        });
      }
    }

    const dokladyWithZAfter = new Set();
    for (const r of afterRows) {
      const texts = [r.Poznamka_dokladu, r.Poznamka, r.Poznamka_zakaznika].filter(Boolean).join(' ');
      if (/Z\s*\d/i.test(texts) || /^\s*Z\s*$/i.test(String(r.Poznamka_dokladu || r.Poznamka || '').trim())) {
        dokladyWithZAfter.add(r.Doklad);
      }
    }

    const report = {
      compared_at: new Date().toISOString(),
      period: before.period,
      before_row_count: before.row_count,
      after_row_count: afterRows.length,
      row_count_delta: afterRows.length - before.row_count,
      note_added_rows: noteAdded,
      note_changed_rows: noteChanged,
      doklady_with_z_marker: [...dokladyWithZAfter].sort(),
      samples,
    };

    const outPath = args.before.replace('_before.json', '_compare.json');
    fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    console.log(`\nReport: ${outPath}`);
  } finally {
    await connection.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
