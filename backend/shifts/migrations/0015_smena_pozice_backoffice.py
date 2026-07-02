from django.db import migrations, models


def set_backoffice_shifts_for_michaela(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    Smena = apps.get_model('shifts', 'Smena')
    users = WebUser.objects.filter(jmeno__iexact='michaela', prijmeni__iexact='smčková')
    if not users.exists():
        users = WebUser.objects.filter(jmeno__iexact='michaela', prijmeni__iexact='smckova')
    for user in users:
        WebUser.objects.filter(pk=user.pk).update(prodejna_id=None)
        Smena.objects.filter(
            user_id=user.pk,
            typ_smeny='prace',
            aktivni=True,
        ).update(pozice_smeny='backoffice')


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0014_mzdovapenalizacemesic_typ_hodnota'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smena',
            name='pozice_smeny',
            field=models.CharField(
                blank=True,
                choices=[
                    ('prodej', 'Prodej'),
                    ('servis', 'Servisní technik'),
                    ('backoffice', 'Backoffice'),
                ],
                default='prodej',
                max_length=20,
                verbose_name='Pozice na směně',
            ),
        ),
        migrations.RunPython(set_backoffice_shifts_for_michaela, migrations.RunPython.noop),
    ]
