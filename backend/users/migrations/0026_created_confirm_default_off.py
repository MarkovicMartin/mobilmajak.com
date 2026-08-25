from django.db import migrations


def disable_created_confirm(apps, schema_editor):
    """Výchozí potvrzení „úkol založen“ vypnout – opt-in v profilu."""
    WebUser = apps.get_model("users", "WebUser")
    for user in WebUser.objects.all().iterator():
        prefs = dict(user.slack_ukoly_prefs or {})
        if prefs.get("created_confirm") is False:
            continue
        prefs["created_confirm"] = False
        user.slack_ukoly_prefs = prefs
        user.save(update_fields=["slack_ukoly_prefs"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0025_cleanup_zero_datetimes"),
    ]

    operations = [
        migrations.RunPython(disable_created_confirm, migrations.RunPython.noop),
    ]
