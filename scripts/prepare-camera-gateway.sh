#!/bin/bash
# Priprava USB balicku pro branu kamer - jeden postup, meni se jen prodejna v prodejny.json
# Pouziti:
#   ./scripts/prepare-camera-gateway.sh sternberk
#   ./scripts/prepare-camera-gateway.sh sternberk /Volumes/USB
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/scripts/camera-gateway/prodejny.json"
PY="${PY:-$ROOT/backend/.venv/bin/python3}"

SLUG="${1:-}"
USB="${2:-}"

if [ -z "$SLUG" ]; then
  echo "Pouziti: $0 <prodejna_slug> [cesta_na_usb]"
  echo ""
  echo "Dostupne prodejny:"
  "$PY" -c "
import json
with open('$MANIFEST') as f:
    for k, v in json.load(f).items():
        print(f\"  {k}: id={v['prodejna_id']}, NVR={v.get('nvr_host','')}\")
"
  exit 1
fi

export ROOT SLUG MANIFEST
"$PY" <<'PY'
import json
import os
import shutil
import sys

root = os.environ["ROOT"]
slug = os.environ["SLUG"]
manifest_path = os.environ["MANIFEST"]

with open(manifest_path, encoding="utf-8") as f:
    stores = json.load(f)

if slug not in stores:
    print(f"Neznama prodejna: {slug}", file=sys.stderr)
    sys.exit(1)

store = stores[slug]
gw_dir = store["gateway_dir"]
secrets_path = os.path.join(root, "secrets", f"camera_motion_{slug}.json")

# motion_secret: zachovat existujici, jinak placeholder
motion_secret = "DOPLNTE_HEX_Z_VPS_CAMERA_MOTION_SECRETS_JSON"
if os.path.isfile(secrets_path):
    with open(secrets_path, encoding="utf-8") as f:
        existing = json.load(f)
    motion_secret = existing.get("motion_secret", motion_secret)
    nvr_pass = existing.get("nvr_pass", "MajakCam2021")
else:
    nvr_pass = "MajakCam2021"

cfg = {
    "mobilmajak_api": "https://mobilmajak.com",
    "prodejna_id": store["prodejna_id"],
    "prodejna_nazev": store["prodejna_nazev"],
    "motion_secret": motion_secret,
    "autodiscover_nvr": True,
    "nvr_host": store.get("nvr_host", ""),
    "nvr_user": "admin",
    "nvr_pass": nvr_pass,
}
if store.get("camera_host"):
    cfg["camera_host"] = store["camera_host"]

os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
with open(secrets_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"OK secrets: {secrets_path}")
print(f"prodejna_id: {store['prodejna_id']}")
print(f"VPS: pridat \"{store['prodejna_id']}\": \"<stejny motion_secret>\" do camera_motion_secrets.json")
print(f"USB: zkopirovat scripts/camera-gateway + scripts/{gw_dir}, config.json ze secrets/")
print(f"PC:  {store['install_cmd']} (cmd jako spravce)")
PY

if [ -n "$USB" ]; then
  if [ ! -d "$USB" ]; then
    echo "USB cesta neexistuje: $USB" >&2
    exit 1
  fi
  GW_DIR="$("$PY" -c "import json; print(json.load(open('$MANIFEST'))['$SLUG']['gateway_dir'])")"
  echo "Kopiruji na $USB ..."
  cp -R "$ROOT/scripts/camera-gateway" "$USB/"
  cp -R "$ROOT/scripts/$GW_DIR" "$USB/"
  SECRETS="$ROOT/secrets/camera_motion_${SLUG}.json"
  if [ -f "$SECRETS" ]; then
    cp "$SECRETS" "$USB/$GW_DIR/config.json"
  fi
  echo "Hotovo: $USB/camera-gateway + $USB/$GW_DIR"
fi
