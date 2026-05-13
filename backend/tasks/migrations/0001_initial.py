from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Ukol',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('ukol', models.CharField(max_length=255, db_column='UKOL')),
                ('priorita', models.CharField(max_length=50, db_column='PRIORITA')),
                ('deadline', models.DateField(blank=True, null=True, db_column='DEADLINE')),
                ('stav', models.CharField(choices=[('novy', 'Nový'), ('v_procesu', 'V procesu'), ('hotovo', 'Hotovo')], default='novy', max_length=20, db_column='STAV')),
                ('id_prodejce_ukol', models.IntegerField(db_column='ID_PRODEJCE_UKOL')),
                ('id_prodejce_zadal', models.IntegerField(db_column='ID_PRODEJCE_ZADAL')),
                ('id_prodejny', models.IntegerField(blank=True, null=True, db_column='ID_PRODEJNY')),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
                ('upraveno', models.DateTimeField(auto_now=True, db_column='UPRAVENO')),
            ],
            options={
                'db_table': 'WEB_UKOLY',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.AddIndex(
            model_name='ukol',
            index=models.Index(fields=['id_prodejce_ukol'], name='idx_ukoly_prodejce'),
        ),
        migrations.AddIndex(
            model_name='ukol',
            index=models.Index(fields=['stav'], name='idx_ukoly_stav'),
        ),
    ]


