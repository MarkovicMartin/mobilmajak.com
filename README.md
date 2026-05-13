# 🚀 WebMajak - Aplikace pro prodejce

> Webová aplikace pro správu prodejců, analytiku prodejů a řízení prodejen

## 📁 Struktura projektu

```
WEB/
├── ZADÁNÍ.md           # 📖 Hlavní dokumentace (PŘEČTI PRVNÍ!)
├── backend/            # 🐍 Django REST API
├── frontend/           # ⚛️ React.js aplikace
├── scripts/            # 🔧 Deployment skripty
└── ZBYTEČNOSTI/        # 📦 Archiv starých souborů
```

## 🔗 Odkazy

- **Produkce:** https://mobilmajak.com
- **Staging:** https://staging.mobilmajak.com
- **VPS:** 194.182.87.138

## 🚀 Rychlý start

### Backend (Django)
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### Frontend (React)
```bash
cd frontend
npm install
npm start
```

## 📚 Dokumentace

Veškeré informace najdeš v **ZADÁNÍ.md**:
- Přístupové údaje
- Struktura databáze
- API endpointy
- Deployment postupy
- Historie změn

## ⚙️ Deployment

**⚠️ DŮLEŽITÉ:** Všechny změny se defaultně nahrávají na **STAGING**!

```bash
# Staging (default)
cd frontend && npm run build
scp -i ~/.ssh/napojeno_ed25519 -r build/* root@194.182.87.138:/home/webmajak/staging/frontend/build/

# Produkce (POUZE na explicitní požádání!)
# ... viz ZADÁNÍ.md
```

## 🛠️ Tech Stack

- **Frontend:** React.js, Recharts, Context API
- **Backend:** Django 4.2, Django REST Framework
- **Database:** MySQL (db.dw300.webglobe.com)
- **Server:** Ubuntu 22.04, Nginx, Gunicorn

## 📊 Funkční moduly

✅ Správa uživatelů | ✅ Novinky | ✅ Analytika | ✅ Můj profil  
✅ Žebříček | ✅ Směny | ✅ Objednávky | ✅ Správa prodejen  
✅ Přístupy | ✅ Interaktivní grafy

---

**Pro detailní informace viz [ZADÁNÍ.md](./ZADÁNÍ.md)**
