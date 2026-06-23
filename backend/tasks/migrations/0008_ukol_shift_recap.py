from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0007_ukol_slack_comment_ref"),
    ]

    operations = [
        migrations.CreateModel(
            name="UkolShiftRecapNotifikace",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("smena_id", models.IntegerField(db_column="SMENA_ID", unique=True)),
                ("user_id", models.IntegerField(db_column="USER_ID")),
                ("datum", models.DateField(db_column="DATUM")),
                ("odeslano_v", models.DateTimeField(auto_now_add=True, db_column="ODESLANO_V")),
            ],
            options={
                "db_table": "WEB_UKOLY_SHIFT_RECAP",
                "indexes": [
                    models.Index(fields=["datum"], name="idx_ukoly_recap_datum"),
                ],
            },
        ),
    ]
