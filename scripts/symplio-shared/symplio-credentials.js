/**
 * Symplio přihlašovací údaje – pouze z env nebo secrets souboru (bez hardcoded fallbacku).
 *
 * Env:
 *   SYMPLIO_USER + SYMPLIO_PASS  (nebo SYMPLIO_PASSWORD)
 *   SYMPLIO_SECRETS_FILE=/path/to/mobilmajak-symplio.json  → { "user": "...", "password": "..." }
 */
const fs = require('fs');

function loadSymplioCredentials() {
  const secretsFile = process.env.SYMPLIO_SECRETS_FILE;
  if (secretsFile) {
    if (!fs.existsSync(secretsFile)) {
      throw new Error(`SYMPLIO_SECRETS_FILE neexistuje: ${secretsFile}`);
    }
    const data = JSON.parse(fs.readFileSync(secretsFile, 'utf8'));
    const user = data.user || data.username || data.login;
    const pass = data.password || data.pass;
    if (!user || !pass) {
      throw new Error(`V ${secretsFile} chybí user/username a password`);
    }
    return { user: String(user), pass: String(pass) };
  }

  const user = process.env.SYMPLIO_USER;
  const pass = process.env.SYMPLIO_PASS || process.env.SYMPLIO_PASSWORD;
  if (!user || !pass) {
    throw new Error(
      'Symplio credentials: nastav SYMPLIO_USER + SYMPLIO_PASS, nebo SYMPLIO_SECRETS_FILE',
    );
  }
  return { user: String(user), pass: String(pass) };
}

module.exports = { loadSymplioCredentials };
