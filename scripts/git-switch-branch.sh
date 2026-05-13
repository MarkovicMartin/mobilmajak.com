#!/bin/bash

# Pomocný skript pro přepínání mezi větvemi
# Použití: ./scripts/git-switch-branch.sh [dev|production|main]

set -e

BRANCH=${1:-dev}

if [ "$BRANCH" != "dev" ] && [ "$BRANCH" != "production" ] && [ "$BRANCH" != "main" ]; then
    echo "❌ Neplatná větev. Použijte: dev, production, nebo main"
    exit 1
fi

echo "🔄 Přepínám se na větev: $BRANCH"

# Zkontrolovat, zda existují necommitnuté změny
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Máte necommitnuté změny. Chcete je:"
    echo "   1) Commitnout"
    echo "   2) Stashnout (dočasně uložit)"
    echo "   3) Zrušit"
    read -p "Volba (1/2/3): " choice
    
    case $choice in
        1)
            read -p "Commit zpráva: " message
            git add .
            git commit -m "$message"
            ;;
        2)
            git stash push -m "Auto-stash před přepnutím na $BRANCH"
            echo "✓ Změny uloženy do stash"
            ;;
        3)
            echo "❌ Zrušeno"
            exit 1
            ;;
        *)
            echo "❌ Neplatná volba"
            exit 1
            ;;
    esac
fi

# Přepnout se na větev
git checkout $BRANCH

# Stáhnout nejnovější změny
echo "📥 Stahuji nejnovější změny..."
git pull origin $BRANCH

echo "✅ Přepnuto na větev: $BRANCH"
echo "📋 Aktuální status:"
git status --short


