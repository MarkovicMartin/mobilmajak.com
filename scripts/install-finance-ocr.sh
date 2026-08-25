#!/bin/bash
# Nainstaluje OCR závislosti pro vyčítání faktur (VS, částky) na VPS.
# Použití z Macu: ./scripts/install-finance-ocr.sh
# Nebo na VPS jako root: bash scripts/install-finance-ocr.sh --local
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${TARGET:-root@194.182.87.138}"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

PACKAGES=(tesseract-ocr tesseract-ocr-ces tesseract-ocr-eng poppler-utils)
VENVS=(/home/webmajak/staging/venv /home/webmajak/webapp/venv)

install_local() {
  echo "=== apt: ${PACKAGES[*]} ==="
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y "${PACKAGES[@]}"

  echo ""
  echo "=== ověření ==="
  command -v tesseract
  tesseract --list-langs 2>&1 | tr '\n' ' '; echo
  command -v pdftoppm
  pdftoppm -v 2>&1 | head -1 || true

  echo ""
  echo "=== Python balíčky ve venv (pypdf + pytesseract) ==="
  for venv in "${VENVS[@]}"; do
    if [ -x "$venv/bin/python" ]; then
      "$venv/bin/python" -m pip install -q 'pypdf==5.9.0' 'pytesseract==0.3.13'
      echo "OK pip: $venv"
    else
      echo "SKIP (není venv): $venv"
    fi
  done

  echo ""
  echo "=== Django check (staging, pokud existuje) ==="
  if [ -x /home/webmajak/staging/venv/bin/python ] && [ -f /home/webmajak/staging/manage.py ]; then
    sudo -u webmajak bash -lc '
      cd /home/webmajak/staging
      set -a
      [ -f .env ] && . ./.env
      set +a
      venv/bin/python manage.py check_finance_ocr
    ' || true
  fi

  echo ""
  echo "Hotovo. OCR pro FA skeny: tesseract (ces+eng) + pdftoppm."
}

if [ "${1:-}" = "--local" ]; then
  install_local
  exit 0
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

echo "=== Install finance OCR on $TARGET ==="
ssh "${SSH_OPTS[@]}" "$TARGET" 'bash -s' -- --local < "$0"
