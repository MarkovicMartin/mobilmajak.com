from django.db import migrations, models


def technik_id_to_servis_uroven(apps, schema_editor):
    WebUser = apps.get_model('users', 'WebUser')
    qs = WebUser.objects.exclude(technik_id__isnull=True).exclude(technik_id=0)
    qs.update(servis_uroven='plny')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_webuser_dovolena_korekce'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='servis_uroven',
            field=models.CharField(
                choices=[
                    ('zadna', 'Nedělá servis'),
                    ('zauceni', 'V zaškolení'),
                    ('plny', 'Schopný servisu'),
                ],
                default='zadna',
                max_length=20,
                verbose_name='Úroveň servisu',
            ),
        ),
        migrations.RunPython(technik_id_to_servis_uroven, migrations.RunPython.noop),
    ]
