from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_webuser_mzda_fields'),
        ('shifts', '0005_alter_smena_prodejna'),
    ]

    operations = [
        migrations.CreateModel(
            name='MzdovaOdmenaMesic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mesic', models.DateField(verbose_name='Měsíc (první den)')),
                ('castka', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Odměna (body)')),
                ('poznamka', models.TextField(blank=True, null=True)),
                ('vytvoreno', models.DateTimeField(auto_now_add=True)),
                ('upraveno', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mzda_odmeny_mesic', to='users.webuser')),
            ],
            options={
                'verbose_name': 'Měsíční odměna',
                'verbose_name_plural': 'Měsíční odměny',
                'db_table': 'WEB_MZDOVAODMENA_MESIC',
                'ordering': ['-mesic'],
                'unique_together': {('user', 'mesic')},
            },
        ),
    ]
