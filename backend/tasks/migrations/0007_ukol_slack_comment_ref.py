from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0006_ukol_slack_dm_recipient"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ukolslacknotifikace",
            name="uniq_ukol_slack_typ_recipient",
        ),
        migrations.AddField(
            model_name="ukolslacknotifikace",
            name="ref_id",
            field=models.IntegerField(
                db_column="REF_ID",
                default=0,
                help_text="ID komentáře u dm_comment; u ostatních typů 0.",
            ),
        ),
        migrations.AddConstraint(
            model_name="ukolslacknotifikace",
            constraint=models.UniqueConstraint(
                fields=("ukol", "typ", "recipient_user_id", "ref_id"),
                name="uniq_ukol_slack_typ_recipient_ref",
            ),
        ),
    ]
