from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ukol',
            name='deadline_cas',
            field=models.TimeField(blank=True, db_column='DEADLINE_CAS', null=True),
        ),
        migrations.AddField(
            model_name='ukol',
            name='precteno_v',
            field=models.DateTimeField(blank=True, db_column='PRECTENO_V', null=True),
        ),
        migrations.AddField(
            model_name='ukol',
            name='typ',
            field=models.CharField(
                choices=[('prirazeny', 'Přiřazený'), ('osobni', 'Osobní')],
                db_column='TYP',
                default='osobni',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='ukol',
            name='priorita',
            field=models.CharField(
                choices=[('nizka', 'Nízká'), ('stredni', 'Střední'), ('vysoka', 'Vysoká')],
                db_column='PRIORITA',
                default='stredni',
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name='UkolKomentar',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('autor_id', models.IntegerField(db_column='AUTOR_ID')),
                ('autor_jmeno', models.CharField(blank=True, db_column='AUTOR_JMENO', default='', max_length=100)),
                ('text', models.TextField(db_column='TEXT')),
                ('vytvoreno', models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')),
                ('ukol', models.ForeignKey(
                    db_column='UKOL_ID',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='komentare',
                    to='tasks.ukol',
                )),
            ],
            options={
                'db_table': 'WEB_UKOLY_KOMENTARE',
                'ordering': ['vytvoreno'],
            },
        ),
        migrations.AddIndex(
            model_name='ukol',
            index=models.Index(fields=['id_prodejny'], name='idx_ukoly_prodejna'),
        ),
        migrations.AddIndex(
            model_name='ukol',
            index=models.Index(fields=['typ'], name='idx_ukoly_typ'),
        ),
    ]
