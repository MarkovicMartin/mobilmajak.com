# Generated manually for data migration
from django.db import migrations


def migrate_prodejna_data(apps, schema_editor):
    """Převede textové hodnoty prodejen na ForeignKey odkazy"""
    WebUser = apps.get_model('users', 'WebUser')
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
    
    for user in WebUser.objects.all():
        if user.prodejna:  # Pokud má uživatel vyplněnou prodejnu
            # Najdeme správnou prodejnu
            prodejna_nazev = prodejna_mapping.get(user.prodejna, user.prodejna)
            
            try:
                prodejna = Prodejna.objects.get(nazev=prodejna_nazev)
                user.prodejna_new = prodejna
                user.save()
                updated_count += 1
                print(f"Převeden uživatel {user.uzivatelske_jmeno}: '{user.prodejna}' -> {prodejna.nazev}")
            except Prodejna.DoesNotExist:
                print(f"⚠️  VAROVÁNÍ: Prodejna '{user.prodejna}' pro uživatele {user.uzivatelske_jmeno} nebyla nalezena")
    
    print(f"✅ Převedeno {updated_count} uživatelů")


def reverse_migrate_prodejna_data(apps, schema_editor):
    """Reverse operace - převede ForeignKey zpět na textové hodnoty"""
    WebUser = apps.get_model('users', 'WebUser')
    
    for user in WebUser.objects.all():
        if user.prodejna_new:
            user.prodejna = user.prodejna_new.nazev
            user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_add_prodejna_fk'),
        ('stores', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_prodejna_data, reverse_migrate_prodejna_data),
    ] 