/**
 * Thin re-export – credentials ze SYMPLIO_SCRIPTS_DIR (default /opt/scripts/symplio-shared).
 */
const path = require('path');
const fs = require('fs');

function resolveSymplioSharedDir() {
  const candidates = [
    process.env.SYMPLIO_SCRIPTS_DIR,
    path.join(__dirname, '../symplio-shared'),
    '/opt/scripts/symplio-shared',
  ].filter(Boolean);
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, 'symplio-credentials.js'))) return dir;
  }
  throw new Error(`symplio-credentials.js nenalezen v: ${candidates.join(', ')}`);
}

module.exports = require(path.join(resolveSymplioSharedDir(), 'symplio-credentials'));
