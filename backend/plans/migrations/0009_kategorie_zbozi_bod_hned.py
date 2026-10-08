from django.db import migrations


def pripis_cekajici(apps, schema_editor):
    from plans.kategorie_zbozi import pripis_body_cekajicim

    pripis_body_cekajicim()


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0008_kategorie_zbozi_zkontrolovano'),
        ('shifts', '0025_vyjezd_navrh'),
    ]

    operations = [
        migrations.RunPython(pripis_cekajici, migrations.RunPython.noop),
    ]
