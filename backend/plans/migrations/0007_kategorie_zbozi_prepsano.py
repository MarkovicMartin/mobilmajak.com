from django.db import migrations, models


def backfill_prepsano(apps, schema_editor):
    Claim = apps.get_model('plans', 'KategorieZboziClaim')
    for claim in Claim.objects.filter(overeno__isnull=False).iterator():
        pred = (claim.kategorie_pred or '').strip()
        po = (claim.kategorie_po or '').strip()
        pred1 = (claim.kategorie_1_pred or '').strip()
        po1 = (claim.kategorie_1_po or '').strip()
        if po and (pred != po or pred1 != po1):
            claim.prepsano = True
            claim.save(update_fields=['prepsano'])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0006_kategorie_zbozi_claim'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategoriezboziclaim',
            name='prepsano',
            field=models.BooleanField(default=False, verbose_name='Kategorie přepsána v databázi'),
        ),
        migrations.RunPython(backfill_prepsano, migrations.RunPython.noop),
    ]
