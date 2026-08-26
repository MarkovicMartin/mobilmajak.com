"""Sloučení podkategorií nákladů – migrace + testy.

Mzdy + oba odvody → Mzdy
Nájmy per prodejna → Nájmy
IT podkategorie → IT a e-shop
Nákup zboží + výkup → Nákup zboží / výkup
"""

MERGE_GROUPS = [
    {
        'target': 'Mzdy',
        'poradi': 100,
        'typ_dph': 'bez',
        'parent': None,
        'sources': [
            'Mzdy – zaměstnanci',
            'Mzdy – bonusy',
            'Odvody',
            'Odvody – sociální',
            'Odvody – zdravotní',
            'Odvody – daň z příjmu',
        ],
    },
    {
        'target': 'Nájmy',
        'poradi': 300,
        'typ_dph': 'z_faktury',
        'parent': None,
        'sources': [
            'Nájem – Globus (GL)',
            'Nájem – Šternberk (ŠT)',
            'Nájem – Zlín (ZL)',
            'Nájem – Přerov (PŘE)',
            'Nájem – Vsetín (VSE)',
            'Nájem – Senimo (SEN)',
            'Nájem – sklad / kancelář',
        ],
    },
    {
        'target': 'IT a e-shop',
        'poradi': 500,
        'typ_dph': 'z_faktury',
        'parent': None,
        'sources': [
            'IT – software / licence',
            'IT – hardware',
            'IT – hosting / domény',
            'E-shop – provize / služby',
        ],
    },
    {
        'target': 'Nákup zboží / výkup',
        'poradi': 901,
        'typ_dph': 'z_faktury',
        'parent': 'Zboží / sklad',
        'rename_from': 'Zboží – nákup sklad',
        'sources': [
            'Zboží – nákup sklad',
            'Výkup',
        ],
    },
]


def sloucit_kategorie(NakladKategorie, NakladPolozka, FioPravidlo):
    """Přesune položky a pravidla na cílové kategorie, zdroje deaktivuje."""
    for group in MERGE_GROUPS:
        parent_id = None
        parent_nazev = group.get('parent')
        if parent_nazev:
            parent = NakladKategorie.objects.filter(nazev=parent_nazev).first()
            parent_id = parent.pk if parent else None

        target = NakladKategorie.objects.filter(nazev=group['target']).first()
        if target is None:
            rename_from = group.get('rename_from')
            if rename_from:
                target = NakladKategorie.objects.filter(nazev=rename_from).first()
            if target is None:
                target = NakladKategorie.objects.create(
                    nazev=group['target'],
                    poradi=group['poradi'],
                    typ_dph=group['typ_dph'],
                    aktivni=True,
                    parent_id=parent_id,
                )
            else:
                target.nazev = group['target']

        target.poradi = group['poradi']
        target.typ_dph = group['typ_dph']
        target.aktivni = True
        target.parent_id = parent_id
        target.save()

        for source_nazev in group['sources']:
            source = NakladKategorie.objects.filter(nazev=source_nazev).first()
            if source is None or source.pk == target.pk:
                continue
            NakladPolozka.objects.filter(kategorie_id=source.pk).update(kategorie_id=target.pk)
            FioPravidlo.objects.filter(kategorie_id=source.pk).update(kategorie_id=target.pk)
            source.aktivni = False
            source.save(update_fields=['aktivni'])
