from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('reklamace', '0002_workflow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reklamacepolozka',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reklamace_vytvorene',
                to='users.webuser',
                verbose_name='Založil',
            ),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='reminder_10d_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Odeslána 10d připomínka'),
        ),
        migrations.AddField(
            model_name='reklamacepolozka',
            name='reminder_30d_slack_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Odeslána 30d Slack připomínka'),
        ),
        migrations.CreateModel(
            name='ReklamaceNotifikace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=300, verbose_name='Zpráva')),
                ('typ', models.CharField(default='reminder_10d', max_length=30, verbose_name='Typ')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True, verbose_name='Přečteno')),
                (
                    'reklamace',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifikace',
                        to='reklamace.reklamacepolozka',
                        verbose_name='Reklamace',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reklamace_notifikace',
                        to='users.webuser',
                        verbose_name='Uživatel',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Reklamace notifikace',
                'verbose_name_plural': 'Reklamace notifikace',
                'db_table': 'WEB_REKLAMACE_NOTIFIKACE',
                'ordering': ['-created_at'],
            },
        ),
    ]
