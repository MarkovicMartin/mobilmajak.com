from django.db import migrations, models
from django.utils import timezone


def backfill_dokonceno_v(apps, schema_editor):
    Ukol = apps.get_model("tasks", "Ukol")
    for task in Ukol.objects.filter(stav="hotovo", dokonceno_v__isnull=True):
        task.dokonceno_v = task.upraveno or timezone.now()
        task.save(update_fields=["dokonceno_v"])


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_ukol_extended"),
    ]

    operations = [
        migrations.AddField(
            model_name="ukol",
            name="dokonceno_v",
            field=models.DateTimeField(blank=True, db_column="DOKONCENO_V", null=True),
        ),
        migrations.RunPython(backfill_dokonceno_v, migrations.RunPython.noop),
    ]
