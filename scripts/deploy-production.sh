#!/bin/bash

# Skript pro nasazení production verze na server
# Použití: ./scripts/deploy-production.sh

set -e

echo "🚀 Nasazuji production verzi na server..."

# Zkontrolovat, že jsme na production větvi
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "production" ]; then
    echo "⚠️  Nejste na production větvi. Aktuální větev: $CURRENT_BRANCH"
    read -p "Chcete pokračovat? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "❌ Zrušeno"
        exit 1
    fi
fi

# Stáhnout nejnovější změny
echo "📥 Kontroluji nejnovější změny..."
git pull origin production

# Build frontend
echo "📦 Builduji frontend..."
cd frontend
npm install
npm run build
cd ..

# Nasazení backendu
echo "⬆️  Nasazuji backend..."
cd backend
bash deploy.sh
cd ..

echo "✅ Nasazení dokončeno!"
echo ""
echo "🌐 Zkontrolujte aplikaci na:"
echo "   Backend API: http://80.211.198.189/api/"
echo "   Health Check: http://80.211.198.189/health/"


