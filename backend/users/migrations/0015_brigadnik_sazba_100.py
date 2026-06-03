"""Brigádník: hodinová sazba 100 bodů/h (dříve výchozí 80)."""
from decimal import Decimal

from django.db import migrations

BRIGADNIK_SAZBA = Decimal('100')


def apply_brigadnik_sazba(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    for user in WebUser.objects.filter(role='BRIGADNIK'):
        if user.mzda_zaklad != BRIGADNIK_SAZBA:
            user.mzda_zaklad = BRIGADNIK_SAZBA
            user.save(update_fields=['mzda_zaklad'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_update_mzda_zaklad_prodejci'),
    ]

    operations = [
        migrations.RunPython(apply_brigadnik_sazba, noop_reverse),
    ]
