from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0002_prodejna_vedouci_oteviraci'),
        ('shifts', '0006_mzdovaodmenamesic'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProdejnaPohybUdalost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pohyb', models.BooleanField(verbose_name='Detekován pohyb')),
                ('cas', models.DateTimeField(db_index=True)),
                ('zdroj', models.CharField(default='gateway', max_length=32)),
                ('vytvoreno', models.DateTimeField(auto_now_add=True)),
                ('prodejna', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pohyb_udalosti',
                    to='stores.prodejna',
                )),
            ],
            options={
                'verbose_name': 'Pohyb na prodejně',
                'verbose_name_plural': 'Pohyb na prodejnách',
                'db_table': 'WEB_PRODEJNA_POHYB_UDALOST',
                'ordering': ['-cas'],
                'indexes': [
                    models.Index(fields=['prodejna', '-cas'], name='idx_pohyb_prodejna_cas'),
                ],
            },
        ),
    ]
