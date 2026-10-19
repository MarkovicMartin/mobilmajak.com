from django.db import migrations, models


def pripis_cekajici(apps, schema_editor):
    from plans.kategorie_zbozi import pripis_body_cekajicim

    pripis_body_cekajicim()


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0009_kategorie_zbozi_bod_hned'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategoriezboziclaim',
            name='kategorie_2_po',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(pripis_cekajici, migrations.RunPython.noop),
    ]
