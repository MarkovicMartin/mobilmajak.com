from django.db import migrations, models


def set_backoffice_shifts_for_michaela(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    Smena = apps.get_model('shifts', 'Smena')
    user_ids = list(
        WebUser.objects.filter(jmeno__iexact='michaela', prijmeni__iexact='smčková').values_list('id', flat=True)
    )
    if not user_ids:
        user_ids = list(
            WebUser.objects.filter(jmeno__iexact='michaela', prijmeni__iexact='smckova').values_list('id', flat=True)
        )
    if not user_ids:
        user_ids = list(WebUser.objects.filter(prijmeni__iexact='smrčková').values_list('id', flat=True))
    if not user_ids:
        user_ids = list(WebUser.objects.filter(prijmeni__iexact='smrckova').values_list('id', flat=True))
    for user_id in user_ids:
        WebUser.objects.filter(pk=user_id).update(prodejna_id=None)
        Smena.objects.filter(
            user_id=user_id,
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
