from django.db import migrations, models


def apply_slack_ukoly_presets(apps, schema_editor):
    WebUser = apps.get_model("users", "WebUser")
    defaults = {
        "assigned_mine": True,
        "created_confirm": True,
        "created_all": False,
        "due_soon_mine": True,
        "due_soon_all": False,
        "overdue_mine": True,
        "overdue_all": False,
        "awaiting_approval": True,
        "completed_mine": True,
    }
    presets = {
        888: {  # Radek Bulandra
            "created_all": True,
            "due_soon_all": True,
            "overdue_all": True,
            "due_soon_mine": False,
            "overdue_mine": False,
            "comment_all": True,
        },
        999: {  # Martin Markovič
            "due_soon_mine": False,
            "created_all": False,
            "due_soon_all": False,
            "overdue_all": False,
            "comment_mine": True,
        },
    }
    for user_id, overrides in presets.items():
        prefs = dict(defaults)
        prefs.update(overrides)
        WebUser.objects.filter(pk=user_id).update(slack_ukoly_prefs=prefs)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0020_webuser_datum_upravy"),
    ]

    operations = [
        migrations.AddField(
            model_name="webuser",
            name="slack_ukoly_prefs",
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name="Slack notifikace úkolů",
            ),
        ),
        migrations.RunPython(apply_slack_ukoly_presets, migrations.RunPython.noop),
    ]
