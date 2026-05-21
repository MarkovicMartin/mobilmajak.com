#!/bin/bash

# Script pro automatické ukládání analytických dat
# Určený pro spouštění pomocí cron jobu každou hodinu

# Nastavení proměnných
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$PROJECT_DIR/venv"
MANAGE_PY="$PROJECT_DIR/manage.py"
LOG_FILE="$PROJECT_DIR/logs/auto_save_analytics.log"

# Vytvoření log adresáře pokud neexistuje
mkdir -p "$PROJECT_DIR/logs"

# Aktivace virtuálního prostředí a spuštění management command
echo "$(date '+%Y-%m-%d %H:%M:%S') - Spouštím automatické ukládání analytických dat" >> "$LOG_FILE"

# Kontrola existence virtuálního prostředí
if [ ! -d "$VENV_PATH" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - CHYBA: Virtuální prostředí neexistuje: $VENV_PATH" >> "$LOG_FILE"
    exit 1
fi

# Kontrola existence manage.py
if [ ! -f "$MANAGE_PY" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - CHYBA: manage.py neexistuje: $MANAGE_PY" >> "$LOG_FILE"
    exit 1
fi

# Aktivace virtuálního prostředí a spuštění commandu
cd "$PROJECT_DIR"
source "$VENV_PATH/bin/activate"

# Spuštění management command s přesměrováním výstupu do logu
python "$MANAGE_PY" auto_save_analytics --verbose >> "$LOG_FILE" 2>&1

# Kontrola výsledku
if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Automatické ukládání dokončeno úspěšně" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - CHYBA: Automatické ukládání selhalo" >> "$LOG_FILE"
fi

echo "-------------------------------------------" >> "$LOG_FILE" 
