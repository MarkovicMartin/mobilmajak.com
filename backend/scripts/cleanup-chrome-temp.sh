#!/bin/bash

# Skript pro automatické čištění Chrome/Chromium dočasných souborů
# Běží denně v cronu pro prevenci zaplnění disku

LOG_FILE="/var/log/cleanup-chrome-temp.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Začínám čištění Chrome temp souborů..." >> "$LOG_FILE"

# Počet souborů před čištěním
BEFORE_COUNT=$(find /tmp -name ".org.chromium.Chromium.*" -type d 2>/dev/null | wc -l)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Nalezeno Chromium temp složek: $BEFORE_COUNT" >> "$LOG_FILE"

# Výpočet velikosti před čištěním
if [ $BEFORE_COUNT -gt 0 ]; then
    BEFORE_SIZE=$(du -sh /tmp/.org.chromium.Chromium.* 2>/dev/null | awk '{sum+=$1} END {print sum}')
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Celková velikost před čištěním: ${BEFORE_SIZE}M" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Žádné temp složky k vyčištění" >> "$LOG_FILE"
fi

# Mazání Chromium temp složek starších než 1 den
find /tmp -name ".org.chromium.Chromium.*" -type d -mtime +1 -exec rm -rf {} + 2>/dev/null

# Mazání všech Chromium temp složek (i nových, pokud actor právě neběží)
# Kontrola, jestli neběží actor (bezpečné mazání)
if ! pgrep -f "web-prodeje-importer" > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Actor neběží, mažu všechny temp složky" >> "$LOG_FILE"
    rm -rf /tmp/.org.chromium.Chromium.* 2>/dev/null
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Actor běží, mažu pouze staré složky" >> "$LOG_FILE"
fi

# Počet souborů po čištění
AFTER_COUNT=$(find /tmp -name ".org.chromium.Chromium.*" -type d 2>/dev/null | wc -l)
DELETED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

echo "$(date '+%Y-%m-%d %H:%M:%S') - Smazáno složek: $DELETED_COUNT" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Zbývá složek: $AFTER_COUNT" >> "$LOG_FILE"

# Kontrola volného místa na disku
FREE_SPACE=$(df -h / | awk 'NR==2 {print $4}')
USED_PERCENT=$(df -h / | awk 'NR==2 {print $5}')
echo "$(date '+%Y-%m-%d %H:%M:%S') - Volné místo na disku: $FREE_SPACE (využito $USED_PERCENT)" >> "$LOG_FILE"

# Varování, pokud je disk plný z více než 80%
USED_PERCENT_NUM=$(echo $USED_PERCENT | sed 's/%//')
if [ $USED_PERCENT_NUM -gt 80 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ⚠️  VAROVÁNÍ: Disk je plný z $USED_PERCENT!" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Čištění dokončeno" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

exit 0

