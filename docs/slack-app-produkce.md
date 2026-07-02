# Slack app „Úkoly“ – detailní nastavení (produkce)

Appka v portalu: **Úkoly** → [api.slack.com/apps](https://api.slack.com/apps)

Všechny **Request URL** míří na **produkci**:

```
https://mobilmajak.com
```

Staging do této appky **nepřidávej** – jedna appka, jeden workspace, produkční endpointy.

---

## Co appka umí

| Funkce | Jak |
|--------|-----|
| Notifikace úkolů (DM) | už běží přes `SLACK_BOT_TOKEN` + cron |
| Zakládání úkolů `/ukol` | slash command → wizard v DM |
| Zakládání z DM | `úkol: …` nebo text během wizardu |
| Tlačítka ve wizardu | Interactivity |

---

## Doporučené pořadí nastavení

1. **Server** – doplnit `SLACK_SIGNING_SECRET` do produkčního `.env` a restart (jinak Events vrátí 503).
2. **Basic Information** – zkopírovat Signing Secret.
3. **OAuth & Permissions** – scopes + Reinstall.
4. **Slash Commands** – `/ukol`.
5. **Interactivity** – URL pro tlačítka.
6. **Event Subscriptions** – `message.im`.
7. **App Home** – záložka Messages.
8. **Test** v DM.

---

## SETTINGS (levé menu)

### 1. Basic Information

**App Credentials**

| Pole | Kam |
|------|-----|
| **Signing Secret** | Show → zkopírovat → VPS `/home/webmajak/app/backend/.env` jako `SLACK_SIGNING_SECRET=...` |

Bez tohoto server vrací `503 slack_not_configured` na všechny Slack endpointy.

**Display Information** (volitelné)

| Pole | Doporučení |
|------|------------|
| App name | `Úkoly` (už máš) |
| Short description | `Úkoly a notifikace MOBILMAJAK` |
| App icon | logo / ikona sešitu |
| Background color | např. `#0066cc` |

**Delete App** – nepoužívat.

---

### 2. Collaborators

- Přidej další adminy workspace, kdo má spravovat appku v portalu.
- Na běh bota nemá vliv.

---

### 3. Socket Mode

- **Vypnuto (OFF).**
- Používáme klasické HTTP Request URL na `mobilmajak.com`, ne WebSocket.

---

### 4. Install App

Tady získáš token po instalaci do workspace.

1. Klikni **Install to Workspace** (nebo **Reinstall** po změně scope).
2. Povol oprávnění.
3. Zkopíruj **Bot User OAuth Token** (`xoxb-...`).
4. Na VPS do `.env`:

```bash
SLACK_BOT_TOKEN=xoxb-...
MOBILMAJAK_APP_URL=https://mobilmajak.com
```

Token už můžeš mít v `secrets/slacktoken.json` – na serveru musí být stejný v `SLACK_BOT_TOKEN`.

---

### 5. Manage Distribution

- Interní appka pro jeden workspace → **nepublikovat** do App Directory.
- Stačí **Install** v bodě 4.

---

## FEATURES (levé menu)

### 6. App Home

**Show Tabs → Home Tab** – může zůstat zapnuté.

**Messages Tab**

| Nastavení | Hodnota |
|-----------|---------|
| **Allow users to send Slash commands and messages from the messages tab** | **Zapnuto** |

Uživatel pak otevře appku „Úkoly“ v postranním panelu / DM a může psát přímo botovi.

**Agent / AI** – nepotřebuješ, vypnuto.

---

### 7. Incoming Webhooks

- **Vypnuto** pro zakládání úkolů.
- Volitelně zapnuto jen pokud používáš `SLACK_TASKS_WEBHOOK_URL` pro kanálové reminder (starší fallback). DM notifikace jedou přes bota.

---

### 8. Interactivity & Shortcuts

**Interactivity**

| Pole | Hodnota |
|------|---------|
| Interactivity | **On** |
| Request URL | `https://mobilmajak.com/api/tasks/slack/interactions/` |

**Save Changes.**

Toto obsluhuje tlačítka ve wizardu (typ úkolu, termín, priorita, Vytvořit / Zrušit).

**Shortcuts / modaly** – zatím nepřidávat (stačí `/ukol` + DM).

---

### 9. Slash Commands

**Create New Command**

| Pole | Hodnota |
|------|---------|
| Command | `/ukol` |
| Request URL | `https://mobilmajak.com/api/tasks/slack/commands/ukol/` |
| Short Description | `Založit úkol v MOBILMAJAK` |
| Usage Hint | `[co je úkolem]` |
| Escape channels, users, links | vypnuto (nebo dle preference) |

**Save.**

**Chování:** Po `/ukol` dostaneš ephemeral hlášku „Poslal jsem ti průvodce…“ a bot pošle **DM** s tlačítky. Wizard probíhá v konverzaci s botem.

Příklady:

```
/ukol
/ukol Zavolat dodavateli o displej
```

---

### 10. OAuth & Permissions

**Redirect URLs** – pro bota nepotřebuješ (neřešíš user OAuth flow).

**Scopes → Bot Token Scopes** – přidej všechny:

| Scope | Proč |
|-------|------|
| `chat:write` | DM notifikace + wizard zprávy |
| `users:read.email` | najít Slack uživatele podle e-mailu (notifikace) |
| `users:read` | z Slack ID zjistit e-mail při `/ukol` |

**User Token Scopes** – nic nepřidávat.

Po přidání scope → zpět na **Install App** → **Reinstall to Workspace**.

---

### 11. Event Subscriptions

**Před uložením URL** musí být na serveru `SLACK_SIGNING_SECRET` + restart gunicornu.

| Pole | Hodnota |
|------|---------|
| Enable Events | **On** |
| Request URL | `https://mobilmajak.com/api/tasks/slack/events/` |

**Pozor:** musí fungovat i bez koncového lomítka (`.../events`), ale doporučujeme **s lomítkem**.

Po Save Slack pošle **url_verification**. Backend odpoví `challenge`. Mělo by být **Verified**.

**Subscribe to bot events** – přidej:

| Event | Proč |
|-------|------|
| `message.im` | text v DM (`úkol: …`, odpovědi v wizardu) |

**Nepřidávat** (zbytečné / šum):

- `message.channels` – bot nečte veřejné kanály
- `app_mention` – nepotřebujeme @Úkoly v kanálu

**Subscribe to events on behalf of users** – ne.

---

### 12. Ostatní položky menu

| Položka | Akce |
|---------|------|
| Workflow Steps | ignorovat |
| Org Level Apps | ignorovat |
| MCP Servers | ignorovat |
| App Manifest | volitelně export zálohy configu |
| Beta Features | ignorovat |

---

## Server – produkční `.env`

Soubor: `/home/webmajak/app/backend/.env`

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=abc123...   # z Basic Information
MOBILMAJAK_APP_URL=https://mobilmajak.com
```

Volitelně:

```bash
SLACK_TASKS_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Po úpravě:**

```bash
# na VPS – název služby ověř u sebe
sudo systemctl restart gunicorn
```

---

## Propojení uživatele Slack ↔ MOBILMAJAK

1. V MOBILMAJAK → profil uživatele → **e-mail**.
2. Musí být **stejný** jako e-mail ve Slacku (firemní).
3. Uživatel musí mít v MOBILMAJAK **aktivní** účet.

Test na serveru:

```bash
source /home/webmajak/app/venv/bin/activate
cd /home/webmajak/app/backend
export DJANGO_SETTINGS_MODULE=webapp.settings_production
set -a && source .env && set +a

curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/auth.test"

curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.lookupByEmail?email=TVOJ@EMAIL.cz"
```

---

## Test od začátku do konce

### A. Endpoint bez podpisu (rychlá kontrola)

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://mobilmajak.com/api/tasks/slack/events/ \
  -H "Content-Type: application/json" -d '{}'
```

| Kód | Význam |
|-----|--------|
| **503** | chybí `SLACK_SIGNING_SECRET` na serveru |
| **403** | secret je, ale chybí platný Slack podpis (normální u curl) |

### B. Ve Slacku

1. Vlevo **DM** → najdi appku **Úkoly** (nebo Apps → Úkoly → Message).
2. Pošli: `/ukol`
3. Měl by přijít průvodce s tlačítky.
4. **Prodejce:** rovnou termín → priorita → vytvořit.
5. **Vedoucí/admin:** volba Osobní / Přiřazený → … → vytvořit.
6. Ověř na https://mobilmajak.com/tasks

### C. DM bez slash

```
úkol: doplnit sklo na výloze
```

---

## Oprávnění ve wizardu

| Role v MOBILMAJAK | Co vidí |
|-------------------|---------|
| Prodejce, brigádník | jen **osobní** úkol (sám sobě) |
| Vedoucí / vedoucí prodejny | osobní + **přiřazený** na své prodejně |
| Admin | vše + úkol **bez prodejny** |

Přiřazený úkol vyžaduje: výsledek, min. 1× DoD, termín, komu.

---

## Časté chyby

| Symptom | Příčina | Oprava |
|---------|---------|--------|
| Event URL: „didn't respond with challenge“ | **chybí `SLACK_SIGNING_SECRET`** na serveru (503) | doplnit `.env` + restart gunicorn, pak **Retry** |
| Event URL: stejná chyba | URL bez `/` na konci (dříve 500) | použít `.../events/` nebo deploy s opravou |
| `/ukol` nic / chyba 503 | secret chybí | viz výše |
| „Není propojený s MOBILMAJAK“ | jiný e-mail | sjednotit e-mail |
| Tlačítka nefungují | Interactivity URL / secret | sekce 8 |
| Text v DM nefunguje | chybí `message.im` | sekce 11 |
| Bot neodpovídá v DM | uživatel nenapsal botovi první | otevři DM s appkou Úkoly |
| Po změně scope nic | starý token | Reinstall app |

---

## Checklist (zaškrtni)

- [ ] `SLACK_SIGNING_SECRET` v produkčním `.env`
- [ ] `SLACK_BOT_TOKEN` v produkčním `.env`
- [ ] `MOBILMAJAK_APP_URL=https://mobilmajak.com`
- [ ] Restart gunicorn po změně `.env`
- [ ] Scopes: `chat:write`, `users:read.email`, `users:read`
- [ ] Reinstall app po scope
- [ ] Slash `/ukol` → produkční URL
- [ ] Interactivity → produkční URL
- [ ] Events → produkční URL + `message.im` verified
- [ ] App Home → Messages tab zapnutá
- [ ] Socket Mode vypnutý
- [ ] Test `/ukol` v DM

---

## Shrnutí URL (copy-paste)

```
Slash:        https://mobilmajak.com/api/tasks/slack/commands/ukol/
Interactivity: https://mobilmajak.com/api/tasks/slack/interactions/
Events:       https://mobilmajak.com/api/tasks/slack/events/
```
