from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0009_slack_task_draft"),
    ]

    operations = [
        migrations.AddField(
            model_name="ukol",
            name="termin_zadani",
            field=models.DateField(blank=True, db_column="TERMIN_ZADANI", null=True),
        ),
    ]
