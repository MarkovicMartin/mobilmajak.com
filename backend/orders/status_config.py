"""Kanban column mapping for Orders redesign (5 main columns)."""

# Main board columns (DB keys → display labels)
MAIN_STATUS_COLUMNS = [
    ("nove", "Nové"),
    ("v_kosiku", "v košíku"),
    ("objednano", "objednáno"),
    ("dorazilo_ceka", "připraveno"),
    ("hotovo", "vyřízeno"),
]

MAIN_STATUS_KEYS = [key for key, _ in MAIN_STATUS_COLUMNS]

# Legacy / filter-only statuses folded into a main column for display
STATUS_COLUMN_FOLD = {
    "predobjednano": "objednano",
}

# Stavy zrušené z UI (legacy data mohou zůstat v DB)
RETIRED_STATUSES = frozenset({"neni_skladem", "storno"})

STATUSES_REQUIRING_DODAVATEL = frozenset({"v_kosiku", "objednano"})


def column_key_for_status(status: str) -> str:
    """Map DB status to the kanban column key."""
    return STATUS_COLUMN_FOLD.get(status, status)
