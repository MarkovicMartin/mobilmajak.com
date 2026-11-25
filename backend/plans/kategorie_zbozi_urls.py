from django.urls import path

from .kategorie_zbozi_views import (
    kategorie_zbozi_audit,
    kategorie_zbozi_audit_kontrola,
    kategorie_zbozi_claim,
    kategorie_zbozi_claim_zrusit,
    kategorie_zbozi_polozky,
    kategorie_zbozi_seznam,
    kategorie_zbozi_automatizace,
    kategorie_zbozi_automatizace_vyresit,
    kategorie_zbozi_zakladani,
    kategorie_zbozi_zakladani_vyresit,
)

urlpatterns = [
    path('polozky/', kategorie_zbozi_polozky, name='kategorie-zbozi-polozky'),
    path('audit/kontrola/', kategorie_zbozi_audit_kontrola, name='kategorie-zbozi-audit-kontrola'),
    path('audit/', kategorie_zbozi_audit, name='kategorie-zbozi-audit'),
    path('automatizace/<int:problem_id>/vyresit/', kategorie_zbozi_automatizace_vyresit, name='kategorie-zbozi-automatizace-vyresit'),
    path('automatizace/', kategorie_zbozi_automatizace, name='kategorie-zbozi-automatizace'),
    path('zakladani/<int:nedostatek_id>/vyresit/', kategorie_zbozi_zakladani_vyresit, name='kategorie-zbozi-zakladani-vyresit'),
    path('zakladani/', kategorie_zbozi_zakladani, name='kategorie-zbozi-zakladani'),
    path('claim/<int:claim_id>/', kategorie_zbozi_claim_zrusit, name='kategorie-zbozi-claim-zrusit'),
    path('claim/', kategorie_zbozi_claim, name='kategorie-zbozi-claim'),
    path('', kategorie_zbozi_seznam, name='kategorie-zbozi-seznam'),
]
