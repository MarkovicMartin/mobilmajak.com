#!/bin/bash

# ČISTIČ TEMP SLOŽEK + orphan Selenium Chrome (hourly cron)
LOG_FILE="/var/log/cistic-temp-slozky.log"
SELENIUM_CLEANUP="${SELENIUM_CLEANUP:-/opt/scripts/selenium-chrome-cleanup.sh}"

echo "$(date '+%Y-%m-%d %H:%M:%S') - 🧹 Začínám čištění Chrome temp složek..." >> "$LOG_FILE"

if [ -x "$SELENIUM_CLEANUP" ]; then
  "$SELENIUM_CLEANUP" >> "$LOG_FILE" 2>&1 || true
else
  BEFORE_COUNT=$(find /tmp -name ".org.chromium.Chromium.*" -type d 2>/dev/null | wc -l)
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Nalezeno Chromium temp složek: $BEFORE_COUNT" >> "$LOG_FILE"
  find /tmp -name ".org.chromium.Chromium.*" -type d -mmin +60 -exec rm -rf {} + 2>/dev/null
  AFTER_COUNT=$(find /tmp -name ".org.chromium.Chromium.*" -type d 2>/dev/null | wc -l)
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Smazáno složek: $((BEFORE_COUNT - AFTER_COUNT))" >> "$LOG_FILE"
fi

FREE_SPACE=$(df -h / | awk 'NR==2 {print $4}')
USED_PERCENT=$(df -h / | awk 'NR==2 {print $5}')
echo "$(date '+%Y-%m-%d %H:%M:%S') - 💿 Volné místo na disku: $FREE_SPACE (využito $USED_PERCENT)" >> "$LOG_FILE"

USED_PERCENT_NUM=$(echo "$USED_PERCENT" | sed 's/%//')
if [ "$USED_PERCENT_NUM" -gt 80 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ⚠️  VAROVÁNÍ: Disk je plný z $USED_PERCENT!" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - 🎉 Čištění dokončeno" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"

exit 0
