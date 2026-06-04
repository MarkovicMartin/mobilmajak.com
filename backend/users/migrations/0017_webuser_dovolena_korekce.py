from decimal import Decimal

from django.db import migrations, models
from django.db.models import Q

DOVOLENA_ZAKLAD = Decimal('160')

# Aktuální zbývající hodiny dovolené (červen 2026)
ZBYVA_PODLE_PRIJMENI = {
    'králik': Decimal('120'),
    'kováčik': Decimal('200'),
    'valenta': Decimal('144'),
    'gabriel': Decimal('74'),
    'babušík': Decimal('160'),
    'kolarčík': Decimal('192'),
    'vychodil': Decimal('176'),
    'markovič': Decimal('120'),
    'krumpolc': Decimal('168'),
    'létal': Decimal('120'),
    'letal': Decimal('120'),
    'karas': Decimal('128'),
    'hekele': Decimal('97'),
}


def _normalize_prijmeni(prijmeni):
    return (prijmeni or '').strip().lower()


def seed_dovolena_zbyva(apps, schema_editor):
    from shifts.vacation_service import (
        DOVOLENA_ROCNI_FOND,
        cerpana_dovolena_rok,
        deficit_fondu_rok,
        prevod_z_predchoziho_roku,
    )

    WebUser = apps.get_model('users', 'WebUser')
    rok = 2026
    qs = WebUser.objects.filter(aktivni=True).filter(
        Q(role__in=('PRODEJCE', 'VEDOUCI'))
        | Q(jmeno__iexact='Martin', prijmeni__iexact='Markovič')
    )
    for user in qs:
        key = _normalize_prijmeni(user.prijmeni)
        zbyva_target = ZBYVA_PODLE_PRIJMENI.get(key)
        if zbyva_target is None:
            continue
        prevod = prevod_z_predchoziho_roku(user.id, rok)
        fond_zaklad = Decimal(str(DOVOLENA_ROCNI_FOND)) + Decimal(str(prevod))
        cerpano_sys = Decimal(str(
            cerpana_dovolena_rok(user.id, rok) + deficit_fondu_rok(user.id, rok)
        ))
        z = Decimal(str(zbyva_target))
        if z + cerpano_sys > fond_zaklad:
            user.dovolena_fond_extra_h = z + cerpano_sys - fond_zaklad
            user.dovolena_korekce_cerpano_h = Decimal('0')
        else:
            user.dovolena_fond_extra_h = Decimal('0')
            user.dovolena_korekce_cerpano_h = fond_zaklad - z - cerpano_sys
        user.save(update_fields=['dovolena_fond_extra_h', 'dovolena_korekce_cerpano_h'])


def unseed_dovolena_zbyva(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    keys = set(ZBYVA_PODLE_PRIJMENI.keys())
    for user in WebUser.objects.filter(role__in=('PRODEJCE', 'VEDOUCI')):
        if _normalize_prijmeni(user.prijmeni) in keys:
            user.dovolena_fond_extra_h = None
            user.dovolena_korekce_cerpano_h = None
            user.save(update_fields=['dovolena_fond_extra_h', 'dovolena_korekce_cerpano_h'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_webuser_mzda_cestovne'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='dovolena_fond_extra_h',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True,
                help_text='Převod nebo korekce nad 160 h ročně.',
                verbose_name='Dovolená – navýšení fondu (h)',
            ),
        ),
        migrations.AddField(
            model_name='webuser',
            name='dovolena_korekce_cerpano_h',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True,
                help_text='Již čerpané hodiny před evidencí ve směnách.',
                verbose_name='Dovolená – korekce čerpání (h)',
            ),
        ),
        migrations.RunPython(seed_dovolena_zbyva, unseed_dovolena_zbyva),
    ]
