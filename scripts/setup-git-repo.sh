#!/bin/bash

# Skript pro počáteční nastavení Git repozitáře
# Použití: ./scripts/setup-git-repo.sh

set -e

echo "🔧 Nastavuji Git repozitář..."

# Zkontrolovat, zda je Git inicializován
if [ ! -d ".git" ]; then
    echo "❌ Git není inicializován. Spusťte: git init"
    exit 1
fi

# Zkontrolovat, zda existuje remote
if ! git remote | grep -q "^origin$"; then
    echo "📝 Přidejte GitHub remote:"
    echo "   git remote add origin https://github.com/VASE_UZIVATELSKE_JMENO/VASE_REPO_JMENO.git"
    read -p "Zadejte URL vašeho GitHub repozitáře (nebo Enter pro přeskočení): " repo_url
    if [ -n "$repo_url" ]; then
        git remote add origin "$repo_url"
        echo "✅ Remote přidán"
    fi
fi

# Vytvořit větve pokud neexistují
if ! git branch | grep -q "dev"; then
    echo "🌿 Vytvářím větev dev..."
    git checkout -b dev
    if git remote | grep -q "^origin$"; then
        git push -u origin dev
    fi
    echo "✅ Větev dev vytvořena"
fi

if ! git branch | grep -q "production"; then
    echo "🌿 Vytvářím větev production..."
    git checkout -b production
    if git remote | grep -q "^origin$"; then
        git push -u origin production
    fi
    echo "✅ Větev production vytvořena"
fi

# Vrátit se na main nebo dev
if git branch | grep -q "main"; then
    git checkout main
elif git branch | grep -q "master"; then
    git checkout master
else
    git checkout dev
fi

echo ""
echo "✅ Git repozitář je nastaven!"
echo ""
echo "📋 Dostupné větve:"
git branch -a
echo ""
echo "💡 Další kroky:"
echo "   1. Commitněte své změny: git add . && git commit -m 'Initial commit'"
echo "   2. Pushněte na GitHub: git push origin main (nebo master)"
echo "   3. Pro práci použijte: ./scripts/git-switch-branch.sh dev"


