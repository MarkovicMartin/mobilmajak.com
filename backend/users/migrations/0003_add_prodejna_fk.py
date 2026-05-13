# Generated manually for data migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('users', '0002_webuser_adresa_webuser_email_webuser_poznamka_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='prodejna_new',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uzivatele', to='stores.prodejna', verbose_name='Prodejna (nové)'),
        ),
    ] 