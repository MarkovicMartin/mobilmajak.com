#!/usr/bin/env node
/**
 * Export servisních položek bez Technika pro manuální kontrolu (XLSX).
 *
 *   node export-servis-bez-technika.js --from 2026-06-01 --to 2026-07-06
 *   node export-servis-bez-technika.js --from 2026-06-01 --out reports/servis_bez_technika.xlsx
 */
const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const { connectToMySQL } = require('./main.js');

function parseArgs(argv) {
    const out = {
        from: '2026-06-01',
        to: new Date().toISOString().slice(0, 10),
        out: null,
    };
    for (let i = 2; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--from') out.from = argv[++i];
        else if (a === '--to') out.to = argv[++i];
        else if (a === '--out') out.out = argv[++i];
    }
    return out;
}

function extractDataBlock(poznamka) {
    if (!poznamka) return '';
    const m = String(poznamka).match(/Data:\s*\{([^}]*)\}/);
    return m ? `{ ${m[1].trim()} }` : '';
}

function explainMissing(kod, dataBlock) {
    if (!dataBlock || dataBlock.trim() === '{ }' || dataBlock.trim() === '{}') {
        return 'Data blok prázdný';
    }
    if (kod && dataBlock.includes(`[P10409 =>`) && kod !== 'P10409') {
        return 'V Data je jen P10409, řádek má jiný kód';
    }
    if (kod && !new RegExp(`\\[${kod.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\s]*=>`).test(dataBlock)) {
        return 'V Data chybí mapování pro tento kód';
    }
    return '';
}

const SQL = `
    SELECT
        Vystaveno AS datum,
        Doklad AS doklad,
        Objednavka AS objednavka,
        Kod AS kod,
        Nazev AS nazev,
        Stredisko AS stredisko,
        Spravce AS spravce,
        Objednavku_zalozil AS objednavku_zalozil,
        ROUND(pocet_kusu * ZISK, 2) AS marze_kc,
        ROUND(pocet_kusu * ZISK * 0.1, 0) AS body_10pct,
        KATEGORIE AS kategorie,
        KATEGORIE_1 AS kategorie_1,
        Poznamka AS poznamka_polozky,
        Poznamka_zakaznika AS poznamka_zakaznika,
        Technik AS technik_v_db
    FROM WEB_PRODEJE_ALL
    WHERE Vystaveno >= ? AND Vystaveno <= ?
      AND objednavku_zalozil LIKE '%servis eda%'
      AND k_servisu = 'ANO'
      AND KATEGORIE LIKE '%!Servis%'
      AND (KATEGORIE_1 IS NULL OR KATEGORIE_1 NOT LIKE '%Služby%')
      AND (Technik IS NULL OR Technik = '')
    ORDER BY Vystaveno, Doklad, Kod
`;

async function main() {
    const args = parseArgs(process.argv);
    const reportsDir = path.join(__dirname, 'reports');
    fs.mkdirSync(reportsDir, { recursive: true });
    const outPath = args.out
        ? (path.isAbsolute(args.out) ? args.out : path.join(__dirname, args.out))
        : path.join(reportsDir, `servis_bez_technika_${args.from}_${args.to}.xlsx`);

    const connection = await connectToMySQL();
    try {
        const [rows] = await connection.execute(SQL, [args.from, args.to]);
        console.log(`Načteno ${rows.length} položek bez Technika (${args.from} .. ${args.to})`);

        const sheetRows = rows.map((r) => {
            const dataBlock = extractDataBlock(r.poznamka_zakaznika);
            const datum = r.datum instanceof Date
                ? r.datum.toISOString().slice(0, 10)
                : String(r.datum || '').slice(0, 10);
            return {
                datum,
                doklad: r.doklad || '',
                objednavka: r.objednavka || '',
                kod: r.kod || '',
                nazev: r.nazev || '',
                stredisko: r.stredisko || '',
                spravce: r.spravce || '',
                marze_kc: Number(r.marze_kc) || 0,
                body_10pct: Number(r.body_10pct) || 0,
                duvod_system: explainMissing(r.kod, dataBlock),
                data_blok: dataBlock,
                objednavku_zalozil: r.objednavku_zalozil || '',
                poznamka_polozky: r.poznamka_polozky || '',
                poznamka_zakaznika: r.poznamka_zakaznika || '',
                kategorie: r.kategorie || '',
                kategorie_1: r.kategorie_1 || '',
                navrzeny_technik: '',
                poznamka_kontrola: '',
            };
        });

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.json_to_sheet(sheetRows, {
            header: [
                'datum', 'doklad', 'objednavka', 'kod', 'nazev', 'stredisko', 'spravce',
                'marze_kc', 'body_10pct', 'duvod_system', 'data_blok',
                'objednavku_zalozil', 'poznamka_polozky', 'poznamka_zakaznika',
                'kategorie', 'kategorie_1', 'navrzeny_technik', 'poznamka_kontrola',
            ],
        });
        ws['!cols'] = [
            { wch: 11 }, { wch: 12 }, { wch: 12 }, { wch: 10 }, { wch: 42 }, { wch: 12 },
            { wch: 18 }, { wch: 10 }, { wch: 10 }, { wch: 32 }, { wch: 48 },
            { wch: 14 }, { wch: 28 }, { wch: 70 }, { wch: 14 }, { wch: 14 },
            { wch: 22 }, { wch: 40 },
        ];
        XLSX.utils.book_append_sheet(wb, ws, 'bez_technika');

        const summary = {};
        for (const r of sheetRows) {
            const key = r.doklad || '?';
            if (!summary[key]) {
                summary[key] = {
                    doklad: key,
                    objednavka: r.objednavka,
                    datum: r.datum,
                    polozek: 0,
                    body_celkem: 0,
                    kody: [],
                };
            }
            summary[key].polozek += 1;
            summary[key].body_celkem += r.body_10pct;
            summary[key].kody.push(r.kod);
        }
        const summaryRows = Object.values(summary).map((s) => ({
            ...s,
            kody: s.kody.join(', '),
        }));
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(summaryRows), 'prehled_dokladu');

        XLSX.writeFile(wb, outPath);
        console.log(`Uloženo: ${outPath} (${fs.statSync(outPath).size} B)`);
    } finally {
        await connection.end();
    }
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
