from django.db import migrations


def add_comment_slack_prefs(apps, schema_editor):
    WebUser = apps.get_model("users", "WebUser")
    presets = {
        888: {"comment_all": True},
        999: {"comment_mine": True},
    }
    for user_id, overrides in presets.items():
        user = WebUser.objects.filter(pk=user_id).first()
        if not user:
            continue
        prefs = dict(user.slack_ukoly_prefs or {})
        prefs.update(overrides)
        user.slack_ukoly_prefs = prefs
        user.save(update_fields=["slack_ukoly_prefs"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0021_webuser_slack_ukoly_prefs"),
    ]

    operations = [
        migrations.RunPython(add_comment_slack_prefs, migrations.RunPython.noop),
    ]
