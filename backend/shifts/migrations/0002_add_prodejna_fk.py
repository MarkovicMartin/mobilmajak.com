# Generated manually for data migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('shifts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='smena',
            name='prodejna_new',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='smeny', to='stores.prodejna', verbose_name='Prodejna (nové)'),
        ),
    ] 