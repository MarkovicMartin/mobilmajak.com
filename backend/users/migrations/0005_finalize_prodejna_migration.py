# Generated manually for finalizing data migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_migrate_prodejna_data'),
    ]

    operations = [
        # Odstraníme staré CharField pole
        migrations.RemoveField(
            model_name='webuser',
            name='prodejna',
        ),
        # Přejmenujeme prodejna_new na prodejna
        migrations.RenameField(
            model_name='webuser',
            old_name='prodejna_new',
            new_name='prodejna',
        ),
    ] 