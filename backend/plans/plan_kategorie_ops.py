"""
Údržba plánových kategorií – sloučení OSTATNI do PRISLUSENSTVI_OSTATNI (Zbytek).
"""
from decimal import Decimal

from django.db import transaction

from .models import PlanCategory, PlanMonth, PlanProdejce, PlanProdejceKategorie

ZBYTEK_KOD = 'PRISLUSENSTVI_OSTATNI'
OSTATNI_KOD = 'OSTATNI'


def _merge_prodejce_kategorie(pp: PlanProdejce, dry_run: bool) -> bool:
    ostatni = PlanProdejceKategorie.objects.filter(
        plan_prodejce=pp, kategorie_kod=OSTATNI_KOD,
    ).first()
    if not ostatni:
        return False
    zbytek, created = PlanProdejceKategorie.objects.get_or_create(
        plan_prodejce=pp,
        kategorie_kod=ZBYTEK_KOD,
        defaults={'pocet_kusu': 0, 'castka': Decimal('0')},
    )
    if dry_run:
        return True
    zbytek.pocet_kusu = (zbytek.pocet_kusu or 0) + (ostatni.pocet_kusu or 0)
    zbytek.castka = (zbytek.castka or Decimal('0')) + (ostatni.castka or Decimal('0'))
    zbytek.save(update_fields=['pocet_kusu', 'castka'])
    ostatni.delete()
    return True


def _merge_store_kategorie(ps, dry_run: bool) -> bool:
    ostatni = PlanCategory.objects.filter(
        plan_prodejna=ps, kategorie_kod=OSTATNI_KOD,
    ).first()
    if not ostatni:
        return False
    zbytek = PlanCategory.objects.filter(
        plan_prodejna=ps, kategorie_kod=ZBYTEK_KOD,
    ).first()
    if dry_run:
        return True
    if zbytek:
        zbytek.castka_kategorie = (
            (zbytek.castka_kategorie or Decimal('0'))
            + (ostatni.castka_kategorie or Decimal('0'))
        )
        zbytek.podil_procenta = (
            (zbytek.podil_procenta or Decimal('0'))
            + (ostatni.podil_procenta or Decimal('0'))
        )
        zbytek.save(update_fields=['castka_kategorie', 'podil_procenta'])
        ostatni.delete()
    else:
        ostatni.kategorie_kod = ZBYTEK_KOD
        ostatni.save(update_fields=['kategorie_kod'])
    return True


@transaction.atomic
def sloucit_ostatni_pro_mesic(rok: int, mesic: int, dry_run: bool = False) -> dict:
    """Sloučí OSTATNI → Zbytek v aktivním plánu měsíce."""
    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return {
            'rok': rok, 'mesic': mesic, 'skipped': True, 'reason': 'no_plan',
            'prodejny': 0, 'prodejci_radky': 0,
        }

    prodejny_cnt = 0
    prodejci_cnt = 0
    for ps in plan.prodejny.prefetch_related('kategorie', 'plany_prodejcu__kategorie'):
        if _merge_store_kategorie(ps, dry_run):
            prodejny_cnt += 1
        for pp in ps.plany_prodejcu.all():
            if _merge_prodejce_kategorie(pp, dry_run):
                prodejci_cnt += 1

    return {
        'rok': rok,
        'mesic': mesic,
        'skipped': False,
        'plan_id': plan.id,
        'prodejny': prodejny_cnt,
        'prodejci_radky': prodejci_cnt,
        'dry_run': dry_run,
    }


def sloucit_ostatni_obdobi(
    rok: int,
    mesic_od: int,
    mesic_do: int = 12,
    dry_run: bool = False,
) -> list[dict]:
    return [
        sloucit_ostatni_pro_mesic(rok, m, dry_run=dry_run)
        for m in range(mesic_od, mesic_do + 1)
    ]
