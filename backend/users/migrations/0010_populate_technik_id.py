# Data migration: vyplní technik_id v WEB_USERS podle jména a příjmení
# Mapování: techniciMap z actoru + 4 doplněné (Daniel M., David V., Monika K., Lukáš H.)

from django.db import migrations


def populate_technik_id(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    # ID -> (jmeno, prijmeni) - z techniciMap (actor) + doplněné
    mapping = [
        (78, 'Miroslav', 'Hoza'),
        (96, 'Martin', 'Šimek'),
        (101, 'Martin', 'Markovič'),
        (102, 'Hugo', 'Šedlbauer'),
        (103, 'Radek', 'Bulandra'),
        (105, 'Jiří', 'Stolín'),
        (106, 'Jakub', 'Šmolc'),
        (108, 'Šimon', 'Erbes'),
        (109, 'Nikol', 'Dostálová'),
        (110, 'Ondřej', 'Půlpábek'),
        (111, 'Lukáš', 'Kováčik'),
        (116, 'Šimon', 'Gabriel'),
        (117, 'Šimon', 'Bílek'),
        (118, 'Tomáš', 'Valenta'),
        (121, 'František', 'Vychodil'),
        (125, 'Adam', 'Kolarčík'),
        (126, 'Aplikace', 'MyRepair.app'),  # speciální případ
        (135, 'Karolína', 'Macková'),
        (148, 'Benny', 'Babušík'),
        (153, 'Tomáš', 'Doležal'),
        (156, 'Patrik', 'Šebák'),
        (157, 'Štěpán', 'Kundera'),
        (167, 'Adéla', 'Koldová'),
        (177, 'Jakub', 'Králík'),
        (178, 'Barbora', 'Ludvigová'),
        (216, 'Lukáš', 'Krumpolc'),
        (231, 'Jiří', 'Pohořelský'),
        (238, 'Kuba', 'Málek'),
        (240, 'Jakub', 'Málek'),
        (261, 'Jan', 'Létal'),
        (268, 'Šimon', 'Kosev'),
        (270, 'Jan', 'Šnyrych'),
        (271, 'Brigádník', 'Majákovský'),
        (290, 'Marek', 'Pich'),
        # Doplněné
        (314, 'Daniel', 'Mahďák'),
        (317, 'David', 'Valčík'),
        (323, 'Monika', 'Křížková'),
        (336, 'Lukáš', 'Hekele'),
    ]
    updated = 0
    for technik_id, jmeno, prijmeni in mapping:
        count = WebUser.objects.filter(jmeno=jmeno, prijmeni=prijmeni).update(technik_id=technik_id)
        updated += count
    if updated:
        print(f'technik_id: aktualizováno {updated} uživatelů.')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_add_technik_id'),
    ]

    operations = [
        migrations.RunPython(populate_technik_id, noop),
    ]
