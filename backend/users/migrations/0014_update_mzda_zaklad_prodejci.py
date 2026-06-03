"""Nastavení měsíčního základu: prodejci/vedoucí 14 000 bodů, Vychodil 17 000 (doplňky vedoucího beze změny)."""
from decimal import Decimal

from django.db import migrations

PRODEJCE_ZAKLAD = Decimal('14000')
VYCHODIL_ZAKLAD = Decimal('17000')
VYCHODIL_TECHNIK_ID = 121


def _is_vychodil(prijmeni, technik_id):
    if technik_id == VYCHODIL_TECHNIK_ID:
        return True
    return (prijmeni or '').strip().lower() == 'vychodil'


def apply_mzda_zaklad(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    for user in WebUser.objects.filter(role__in=('PRODEJCE', 'VEDOUCI')):
        castka = VYCHODIL_ZAKLAD if _is_vychodil(user.prijmeni, user.technik_id) else PRODEJCE_ZAKLAD
        if user.mzda_zaklad != castka:
            user.mzda_zaklad = castka
            user.save(update_fields=['mzda_zaklad'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_role_brigadnik_mzda_fixni'),
    ]

    operations = [
        migrations.RunPython(apply_mzda_zaklad, noop_reverse),
    ]
