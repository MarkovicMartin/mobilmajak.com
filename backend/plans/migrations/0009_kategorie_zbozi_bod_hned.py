from django.db import migrations


def pripis_cekajici(apps, schema_editor):
    # Sloupec kategorie_2_po přibývá až v 0010. Připsání bodů je tam.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0008_kategorie_zbozi_zkontrolovano'),
        ('shifts', '0025_vyjezd_navrh'),
    ]

    operations = [
        migrations.RunPython(pripis_cekajici, migrations.RunPython.noop),
    ]
