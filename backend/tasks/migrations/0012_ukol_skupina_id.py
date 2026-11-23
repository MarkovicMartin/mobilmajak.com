from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0011_ukol_slack_dm_started"),
    ]

    operations = [
        migrations.AddField(
            model_name="ukol",
            name="skupina_id",
            field=models.CharField(
                blank=True,
                db_column="SKUPINA_ID",
                db_index=True,
                default="",
                help_text="Společná dávka: stejné zadání pro víc lidí, každý má vlastní stav.",
                max_length=32,
            ),
        ),
    ]
