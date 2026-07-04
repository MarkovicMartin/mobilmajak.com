# Sdílený rozvrh Packeta importu a Symplio poznámek dokladů.
# Úprava slotů zde se projeví v install-packeta-cron.sh (oba crony).
#
# Použití: source "$(dirname "$0")/packeta-cron-schedule.sh"

# Minuty mezi pobočkami v jedné vlně Packety (typický běh 3–6 min, timeout 10 min)
PACKETA_CRON_STAGGER_MIN="${PACKETA_CRON_STAGGER_MIN:-15}"
PACKETA_CRON_AUDIT_STAGGER_MIN="${PACKETA_CRON_AUDIT_STAGGER_MIN:-20}"

# Včera – první pobočka (Globus)
PACKETA_CRON_YESTERDAY_HOUR="${PACKETA_CRON_YESTERDAY_HOUR:-5}"
PACKETA_CRON_YESTERDAY_MIN="${PACKETA_CRON_YESTERDAY_MIN:-0}"

# Dnes – začátky vln (formát HH:MM nebo H:MM)
PACKETA_CRON_TODAY_SLOTS=(
  "${PACKETA_CRON_TODAY_SLOT_1:-10:0}"
  "${PACKETA_CRON_TODAY_SLOT_2:-13:0}"
  "${PACKETA_CRON_TODAY_SLOT_3:-16:30}"
  "${PACKETA_CRON_TODAY_SLOT_4:-20:0}"
)

# Audit 7 dní – neděle, první pobočka
PACKETA_CRON_AUDIT_HOUR="${PACKETA_CRON_AUDIT_HOUR:-22}"
PACKETA_CRON_AUDIT_MIN="${PACKETA_CRON_AUDIT_MIN:-0}"
PACKETA_CRON_AUDIT_DOW="${PACKETA_CRON_AUDIT_DOW:-0}"

# Symplio poznámky dokladů – kolik minut před první pobočkou Packety v dané vlně
SYMPLIO_DOKLAD_NOTES_OFFSET_MIN="${SYMPLIO_DOKLAD_NOTES_OFFSET_MIN:-15}"

# Parsuje slot "16:30" → nastaví _SLOT_H a _SLOT_M
parse_cron_slot() {
  local slot="$1"
  _SLOT_H="${slot%%:*}"
  _SLOT_M="${slot##*:}"
}

# Vrátí "MIN HOUR" pro cron (odečte offset minut od base_h:base_m, wrap přes půlnoc)
cron_time_before_offset() {
  local base_h=$1 base_m=$2 offset=$3
  local total=$(( base_h * 60 + base_m - offset ))
  while [ "$total" -lt 0 ]; do total=$(( total + 24 * 60 )); done
  total=$(( total % (24 * 60) ))
  printf '%d %d' $(( total % 60 )) $(( total / 60 ))
}
