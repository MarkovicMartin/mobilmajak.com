from django.db import migrations

DEFAULT_KATEGORIE = [
    ('Nájem', 10),
    ('Energie', 20),
    ('Odvody', 30),
    ('Marketing', 40),
    ('IT', 50),
    ('Účetnictví', 60),
    ('Ostatní', 90),
]


def seed_kategorie(apps, schema_editor):
    NakladKategorie = apps.get_model('finance', 'NakladKategorie')
    for nazev, poradi in DEFAULT_KATEGORIE:
        NakladKategorie.objects.get_or_create(nazev=nazev, defaults={'poradi': poradi, 'aktivni': True})


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_kategorie, migrations.RunPython.noop),
    ]
