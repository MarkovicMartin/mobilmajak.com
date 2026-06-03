"""Sdílené DB helpery pro analytics views."""
from .receipt_metrics import count_active_receipts


def count_active_receipts_from_queryset(queryset):
    """Varianta 1: jen doklady s alespoň jednou položkou ≥29 Kč s kódem."""
    return count_active_receipts(queryset)
