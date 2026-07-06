"""Rozšíření kategorií dle struktury Excelu (skupiny + podkategorie)."""
from django.db import migrations

# (nazev, poradi, typ_dph, parent_nazev nebo None)
KATEGORIE_TREE = [
    # Skupiny (parent=None)
    ('Mzdy', 100, 'bez', None),
    ('Odvody', 110, 'bez', None),
    ('Reklama', 200, 'z_faktury', None),
    ('Nájmy', 300, 'z_faktury', None),
    ('Energie', 400, 'z_faktury', None),
    ('IT a e-shop', 500, 'z_faktury', None),
    ('Doprava', 600, 'z_faktury', None),
    ('Leasing', 700, 'bez', None),
    ('Spotřeba prodejny', 800, 'z_faktury', None),
    ('Zboží / sklad', 900, 'z_faktury', None),
    ('Účetnictví a právní', 950, 'z_faktury', None),
    ('Ostatní', 990, 'z_faktury', None),
    # Mzdy – podkategorie
    ('Mzdy – zaměstnanci', 101, 'bez', 'Mzdy'),
    ('Mzdy – bonusy', 102, 'bez', 'Mzdy'),
    # Odvody
    ('Odvody – sociální', 111, 'bez', 'Odvody'),
    ('Odvody – zdravotní', 112, 'bez', 'Odvody'),
    ('Odvody – daň z příjmu', 113, 'bez', 'Odvody'),
    # Reklama per prodejna (prefixy z Excelu)
    ('Reklama – Globus (GL)', 201, 'z_faktury', 'Reklama'),
    ('Reklama – Šternberk (ŠT)', 202, 'z_faktury', 'Reklama'),
    ('Reklama – Zlín (ZL)', 203, 'z_faktury', 'Reklama'),
    ('Reklama – Přerov (PŘE)', 204, 'z_faktury', 'Reklama'),
    ('Reklama – Vsetín (VSE)', 205, 'z_faktury', 'Reklama'),
    ('Reklama – Senimo (SEN)', 206, 'z_faktury', 'Reklama'),
    ('Reklama – firma / online', 207, 'z_faktury', 'Reklama'),
    # Nájmy per prodejna
    ('Nájem – Globus (GL)', 301, 'z_faktury', 'Nájmy'),
    ('Nájem – Šternberk (ŠT)', 302, 'z_faktury', 'Nájmy'),
    ('Nájem – Zlín (ZL)', 303, 'z_faktury', 'Nájmy'),
    ('Nájem – Přerov (PŘE)', 304, 'z_faktury', 'Nájmy'),
    ('Nájem – Vsetín (VSE)', 305, 'z_faktury', 'Nájmy'),
    ('Nájem – Senimo (SEN)', 306, 'z_faktury', 'Nájmy'),
    ('Nájem – sklad / kancelář', 307, 'z_faktury', 'Nájmy'),
    # Energie
    ('Energie – elektřina', 401, 'z_faktury', 'Energie'),
    ('Energie – plyn', 402, 'z_faktury', 'Energie'),
    ('Energie – voda', 403, 'z_faktury', 'Energie'),
    ('Energie – teplo', 404, 'z_faktury', 'Energie'),
    # IT
    ('IT – software / licence', 501, 'z_faktury', 'IT a e-shop'),
    ('IT – hardware', 502, 'z_faktury', 'IT a e-shop'),
    ('IT – hosting / domény', 503, 'z_faktury', 'IT a e-shop'),
    ('E-shop – provize / služby', 504, 'z_faktury', 'IT a e-shop'),
    # Doprava
    ('Doprava – Zásilkovna / kurýr', 601, 'z_faktury', 'Doprava'),
    ('Doprava – palivo', 602, 'z_faktury', 'Doprava'),
    ('Doprava – servis vozidel', 603, 'z_faktury', 'Doprava'),
    # Leasing
    ('Leasing – vozidla', 701, 'bez', 'Leasing'),
    ('Leasing – technika', 702, 'bez', 'Leasing'),
    # Spotřeba prodejny
    ('Spotřeba – úklid', 801, 'z_faktury', 'Spotřeba prodejny'),
    ('Spotřeba – kancelář', 802, 'z_faktury', 'Spotřeba prodejny'),
    ('Spotřeba – občerstvení', 803, 'z_faktury', 'Spotřeba prodejny'),
    # Zboží
    ('Zboží – nákup sklad', 901, 'z_faktury', 'Zboží / sklad'),
    ('Zboží – reklamace / škody', 902, 'z_faktury', 'Zboží / sklad'),
]

# Mapování starých kategorií z 0002 na nové skupiny
LEGACY_RENAME = {
    'Nájem': 'Nájmy',
    'Marketing': 'Reklama',
    'IT': 'IT a e-shop',
}


def seed_excel_kategorie(apps, schema_editor):
    NakladKategorie = apps.get_model('finance', 'NakladKategorie')

    for old, new in LEGACY_RENAME.items():
        NakladKategorie.objects.filter(nazev=old).update(nazev=new)

    parents = {}
    for nazev, poradi, typ_dph, parent_nazev in KATEGORIE_TREE:
        if parent_nazev is None:
            obj, _ = NakladKategorie.objects.update_or_create(
                nazev=nazev,
                defaults={'poradi': poradi, 'typ_dph': typ_dph, 'aktivni': True, 'parent_id': None},
            )
            parents[nazev] = obj.id

    for nazev, poradi, typ_dph, parent_nazev in KATEGORIE_TREE:
        if parent_nazev is None:
            continue
        parent_id = parents.get(parent_nazev)
        NakladKategorie.objects.update_or_create(
            nazev=nazev,
            defaults={
                'poradi': poradi,
                'typ_dph': typ_dph,
                'aktivni': True,
                'parent_id': parent_id,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_f1_dph_doklad_zustatek'),
    ]

    operations = [
        migrations.RunPython(seed_excel_kategorie, migrations.RunPython.noop),
    ]
