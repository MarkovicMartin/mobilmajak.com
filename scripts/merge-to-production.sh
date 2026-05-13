#!/bin/bash

# Skript pro sloučení dev větve do production
# Použití: ./scripts/merge-to-production.sh

set -e

echo "🚀 Slučuji dev do production..."

# Zkontrolovat, že jsme na dev větvi
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo "⚠️  Nejste na dev větvi. Aktuální větev: $CURRENT_BRANCH"
    read -p "Chcete pokračovat? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "❌ Zrušeno"
        exit 1
    fi
fi

# Zkontrolovat necommitnuté změny
if ! git diff-index --quiet HEAD --; then
    echo "❌ Máte necommitnuté změny. Prosím commitněte nebo stashněte změny před merge."
    exit 1
fi

# Stáhnout nejnovější změny
echo "📥 Stahuji nejnovější změny z dev..."
git pull origin dev

# Přepnout se na production
echo "🔄 Přepínám se na production..."
git checkout production

# Stáhnout nejnovější production
echo "📥 Stahuji nejnovější změny z production..."
git pull origin production

# Sloučit dev do production
echo "🔀 Slučuji dev do production..."
git merge dev --no-ff -m "Merge dev into production: $(date '+%Y-%m-%d %H:%M:%S')"

# Zobrazit změny
echo "📋 Změny které budou nasazeny:"
git log production ^origin/production --oneline

# Potvrdit push
read -p "Chcete pushnout změny na GitHub? (y/n): " confirm
if [ "$confirm" = "y" ]; then
    echo "⬆️  Pushuji na GitHub..."
    git push origin production
    echo "✅ Změny pushnuty na GitHub"
    echo ""
    echo "📝 Další kroky:"
    echo "   1. Pokud máte GitHub Actions, nasazení proběhne automaticky"
    echo "   2. Nebo spusťte: ./scripts/deploy-production.sh"
else
    echo "⚠️  Změny jsou pouze lokálně. Pro nasazení spusťte:"
    echo "   git push origin production"
fi

# Vrátit se zpět na dev
read -p "Chcete se vrátit na dev větev? (y/n): " back_to_dev
if [ "$back_to_dev" = "y" ]; then
    git checkout dev
    echo "✅ Vráceno na dev větev"
fi


