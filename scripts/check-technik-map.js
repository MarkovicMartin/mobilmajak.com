const mysql = require('mysql2/promise');
const fs = require('fs');
const path = process.argv[2] || '/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/main.js';
const src = fs.readFileSync(path, 'utf8');
const m = src.match(/const MYSQL_CONFIG = \{[\s\S]*?\};/);
if (!m) {
  console.error('MYSQL_CONFIG not found');
  process.exit(1);
}
eval(m[0].replace('const MYSQL_CONFIG', 'global.MYSQL_CONFIG'));

(async () => {
  const c = await mysql.createConnection(MYSQL_CONFIG);
  const [rows] = await c.execute(
    `SELECT id, jmeno, prijmeni, technik_id FROM WEB_USERS
     WHERE technik_id IN (148,343)
        OR (prijmeni IN ('Babušík','Karas') AND jmeno IN ('Artur','Benny','Dominik'))`
  );
  console.log('WEB_USERS rows:', JSON.stringify(rows, null, 2));

  const [mapRows] = await c.execute(
    'SELECT technik_id, jmeno, prijmeni FROM WEB_USERS WHERE technik_id IS NOT NULL'
  );
  const technici = {};
  for (const r of mapRows) {
    const jmeno = (r.jmeno || '').trim();
    const prijmeni = (r.prijmeni || '').trim();
    if (r.technik_id != null && (jmeno || prijmeni)) {
      technici[Number(r.technik_id)] = [jmeno, prijmeni].filter(Boolean).join(' ');
    }
  }
  console.log('Actor map[148]:', technici[148]);
  console.log('Actor map[343]:', technici[343]);
  console.log('Total technici in map:', Object.keys(technici).length);
  await c.end();
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
