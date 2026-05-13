# Generated manually for finalizing data migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0003_migrate_prodejna_data'),
    ]

    operations = [
        # Nejdřív odstraníme unique_together constraint, který používá staré pole
        migrations.AlterUniqueTogether(
            name='smena',
            unique_together=set(),
        ),
        # Odstraníme staré CharField pole
        migrations.RemoveField(
            model_name='smena',
            name='prodejna',
        ),
        # Přejmenujeme prodejna_new na prodejna
        migrations.RenameField(
            model_name='smena',
            old_name='prodejna_new',
            new_name='prodejna',
        ),
        # Obnovíme unique_together constraint s novým polem
        migrations.AlterUniqueTogether(
            name='smena',
            unique_together={('user', 'datum', 'prodejna')},
        ),
    ] 