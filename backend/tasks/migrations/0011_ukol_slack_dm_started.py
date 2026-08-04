from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0010_ukol_termin_zadani"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ukolslacknotifikace",
            name="typ",
            field=models.CharField(
                choices=[
                    ("due_soon", "Blíží se termín (webhook)"),
                    ("overdue", "Po termínu (webhook)"),
                    ("dm_assigned", "DM – přiřazení"),
                    ("dm_due_soon", "DM – blíží se termín"),
                    ("dm_overdue", "DM – po termínu"),
                    ("dm_completed", "DM – hotovo"),
                    ("dm_awaiting_approval", "DM – čeká schválení"),
                    ("dm_started", "DM – začal pracovat"),
                    ("dm_created", "DM – potvrzení zadavateli"),
                    ("dm_comment", "DM – nový komentář"),
                ],
                db_column="TYP",
                max_length=30,
            ),
        ),
    ]
