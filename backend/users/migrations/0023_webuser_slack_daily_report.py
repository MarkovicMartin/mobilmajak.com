from django.db import migrations, models


def enable_daily_report_defaults(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    WebUser.objects.filter(
        jmeno__iexact='Radek',
        prijmeni__iexact='Bulandra',
        aktivni=True,
    ).update(slack_daily_report=True)
    WebUser.objects.filter(
        jmeno__iexact='Petr',
        prijmeni__iexact='Valenta',
        aktivni=True,
    ).update(slack_daily_report=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_slack_comment_prefs'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='slack_daily_report',
            field=models.BooleanField(
                default=False,
                verbose_name='Slack denní report prodejů',
            ),
        ),
        migrations.RunPython(enable_daily_report_defaults, migrations.RunPython.noop),
    ]
