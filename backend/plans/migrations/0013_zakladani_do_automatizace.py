from django.db import migrations


def prekopirovat(apps, schema_editor):
    Stary = apps.get_model('plans', 'ZakladaniNedostatek')
    Novy = apps.get_model('plans', 'AutomatizaceKaretProblem')
    for row in Stary.objects.all():
        if Novy.objects.filter(kod=row.kod, typ=row.typ, text=row.text, stav=row.stav).exists():
            continue
        Novy.objects.create(
            kod=row.kod,
            zbozi_id=row.zbozi_id,
            nazev=row.nazev,
            typ=row.typ,
            text=row.text,
            stav=row.stav,
            vytvoreno=row.vytvoreno,
            vyreseno=row.vyreseno,
            vyresil_id=row.vyresil_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0012_automatizace_karet'),
    ]

    operations = [
        migrations.RunPython(prekopirovat, migrations.RunPython.noop),
    ]
