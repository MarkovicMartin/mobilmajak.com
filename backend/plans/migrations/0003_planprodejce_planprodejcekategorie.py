# Generated manually for Fáze 3 – PlanProdejce + PlanProdejceKategorie

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0002_plancategory_prumerna_cena_za_kus'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanProdejce',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('plan_prodejna', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='plany_prodejcu',
                    to='plans.planstore',
                    verbose_name='Plán prodejny',
                )),
                ('uzivatel', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='plany_prodejce',
                    to='users.webuser',
                    verbose_name='Prodejce',
                )),
            ],
            options={
                'verbose_name': 'Plán prodejce',
                'verbose_name_plural': 'Plány prodejců',
                'db_table': 'WEB_PLANS_PRODEJCE',
                'ordering': ['uzivatel__jmeno', 'uzivatel__prijmeni'],
                'unique_together': {('plan_prodejna', 'uzivatel')},
            },
        ),
        migrations.CreateModel(
            name='PlanProdejceKategorie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('kategorie_kod', models.CharField(
                    choices=[
                        ('NOVE_TELEFONY', 'Telefony nové'),
                        ('BAZAROVE_TELEFONY', 'Telefony bazarové'),
                        ('PRISLUSENSTVI', 'Příslušenství'),
                        ('PRISLUSENSTVI_SKLA', 'Příslušenství – Skla'),
                        ('PRISLUSENSTVI_OBALY', 'Příslušenství – Obaly'),
                        ('PRISLUSENSTVI_OSTATNI', 'Příslušenství – Ostatní'),
                        ('SLUZBY', 'Služby'),
                        ('SERVIS', 'Servis'),
                        ('OSTATNI', 'Ostatní'),
                    ],
                    max_length=30,
                    verbose_name='Kategorie',
                )),
                ('pocet_kusu', models.IntegerField(default=0, verbose_name='Plánované kusy')),
                ('castka', models.DecimalField(
                    decimal_places=2, default=0, max_digits=12, verbose_name='Plánovaná částka (Kč)'
                )),
                ('plan_prodejce', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kategorie',
                    to='plans.planprodejce',
                    verbose_name='Plán prodejce',
                )),
            ],
            options={
                'verbose_name': 'Plán prodejce – kategorie',
                'verbose_name_plural': 'Plány prodejců – kategorie',
                'db_table': 'WEB_PLANS_PRODEJCE_KAT',
                'ordering': ['kategorie_kod'],
                'unique_together': {('plan_prodejce', 'kategorie_kod')},
            },
        ),
    ]
