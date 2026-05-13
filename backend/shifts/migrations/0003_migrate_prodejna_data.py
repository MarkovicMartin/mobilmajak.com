# Generated manually for data migration
from django.db import migrations


def migrate_smena_prodejna_data(apps, schema_editor):
    """Převede textové hodnoty prodejen na ForeignKey odkazy"""
    Smena = apps.get_model('shifts', 'Smena')
    Prodejna = apps.get_model('stores', 'Prodejna')
    
    # Mapování názvů prodejen
    prodejna_mapping = {
        'Globus': 'Globus',
        'Senimo': 'Senimo',
        'Hlavní sklad - Senimo': 'Senimo',
        'Zlín': 'Zlín',
        'Čepkov': 'Zlín',
        'Přerov': 'Přerov',
        'Vsetín': 'Vsetín',
        'Šternberk': 'Šternberk',
    }
    
    updated_count = 0
    
    for smena in Smena.objects.all():
        if smena.prodejna:  # Pokud má směna vyplněnou prodejnu
            # Najdeme správnou prodejnu
            prodejna_nazev = prodejna_mapping.get(smena.prodejna, smena.prodejna)
            
            try:
                prodejna = Prodejna.objects.get(nazev=prodejna_nazev)
                smena.prodejna_new = prodejna
                smena.save()
                updated_count += 1
                print(f"Převedena směna {smena.id}: '{smena.prodejna}' -> {prodejna.nazev}")
            except Prodejna.DoesNotExist:
                print(f"⚠️  VAROVÁNÍ: Prodejna '{smena.prodejna}' pro směnu {smena.id} nebyla nalezena")
    
    print(f"✅ Převedeno {updated_count} směn")


def reverse_migrate_smena_prodejna_data(apps, schema_editor):
    """Reverse operace - převede ForeignKey zpět na textové hodnoty"""
    Smena = apps.get_model('shifts', 'Smena')
    
    for smena in Smena.objects.all():
        if smena.prodejna_new:
            smena.prodejna = smena.prodejna_new.nazev
            smena.save()


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0002_add_prodejna_fk'),
        ('stores', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_smena_prodejna_data, reverse_migrate_smena_prodejna_data),
    ] 