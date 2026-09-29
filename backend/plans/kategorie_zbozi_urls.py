from django.urls import path

from .kategorie_zbozi_views import (
    kategorie_zbozi_audit,
    kategorie_zbozi_audit_kontrola,
    kategorie_zbozi_claim,
    kategorie_zbozi_claim_zrusit,
    kategorie_zbozi_polozky,
    kategorie_zbozi_seznam,
)

urlpatterns = [
    path('polozky/', kategorie_zbozi_polozky, name='kategorie-zbozi-polozky'),
    path('audit/kontrola/', kategorie_zbozi_audit_kontrola, name='kategorie-zbozi-audit-kontrola'),
    path('audit/', kategorie_zbozi_audit, name='kategorie-zbozi-audit'),
    path('claim/<int:claim_id>/', kategorie_zbozi_claim_zrusit, name='kategorie-zbozi-claim-zrusit'),
    path('claim/', kategorie_zbozi_claim, name='kategorie-zbozi-claim'),
    path('', kategorie_zbozi_seznam, name='kategorie-zbozi-seznam'),
]
