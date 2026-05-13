from django.db import migrations, models


LOCK_MODE_CHOICES = [
    ('none', 'Auto (dopočet)'),
    ('pct',  'Zamčené procento'),
    ('kc',   'Zamčená absolutní částka'),
]


def zamknuto_to_lock_mode(apps, schema_editor):
    """BC převod: staré zamknuto=True znamená zamčené procento (lock_mode='pct')."""
    PlanStore = apps.get_model('plans', 'PlanStore')
    PlanStore.objects.filter(zamknuto=True).update(lock_mode='pct')


def lock_mode_to_zamknuto(apps, schema_editor):
    """Reverzní převod: lock_mode='pct' → zamknuto=True, ostatní False."""
    PlanStore = apps.get_model('plans', 'PlanStore')
    PlanStore.objects.filter(lock_mode='pct').update(zamknuto=True)
    PlanStore.objects.exclude(lock_mode='pct').update(zamknuto=False)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0003_planprodejce_planprodejcekategorie'),
    ]

    operations = [
        migrations.AddField(
            model_name='planmonth',
            name='total_lock',
            field=models.BooleanField(default=False, verbose_name='Celková částka pevná'),
        ),
        migrations.AddField(
            model_name='planstore',
            name='lock_mode',
            field=models.CharField(
                choices=LOCK_MODE_CHOICES, default='none', max_length=8,
                verbose_name='Režim zámku prodejny',
            ),
        ),
        migrations.AddField(
            model_name='planstore',
            name='servis_lock_mode',
            field=models.CharField(
                choices=LOCK_MODE_CHOICES, default='none', max_length=8,
                verbose_name='Režim zámku prodej/servis',
            ),
        ),
        migrations.AlterField(
            model_name='planstore',
            name='zamknuto',
            field=models.BooleanField(default=False, verbose_name='Zamknuto (legacy)'),
        ),
        migrations.AddField(
            model_name='plancategory',
            name='lock_mode',
            field=models.CharField(
                choices=LOCK_MODE_CHOICES, default='none', max_length=8,
                verbose_name='Režim zámku kategorie',
            ),
        ),
        migrations.AddField(
            model_name='planprodejcekategorie',
            name='lock_mode',
            field=models.CharField(
                choices=LOCK_MODE_CHOICES, default='none', max_length=8,
                verbose_name='Režim zámku (prodejce × kategorie)',
            ),
        ),
        migrations.RunPython(zamknuto_to_lock_mode, lock_mode_to_zamknuto),
    ]
