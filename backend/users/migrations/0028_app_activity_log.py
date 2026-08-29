from django.db import migrations, models
import users.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_webuser_pozice_od'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppActivityLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(db_index=True)),
                ('vytvoreno', users.fields.SafeDateTimeField(auto_now_add=True, db_index=True)),
                ('ip', models.CharField(blank=True, default='', max_length=64)),
                ('module', models.CharField(blank=True, default='', max_length=32)),
                ('path', models.CharField(blank=True, default='', max_length=200)),
                ('method', models.CharField(blank=True, default='', max_length=8)),
                ('status_code', models.PositiveSmallIntegerField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'App activity log',
                'verbose_name_plural': 'App activity logy',
                'db_table': 'app_activity_log',
                'ordering': ['-vytvoreno'],
            },
        ),
        migrations.AddIndex(
            model_name='appactivitylog',
            index=models.Index(fields=['user_id', 'vytvoreno'], name='app_act_user_cas_idx'),
        ),
    ]
