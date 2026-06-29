from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_seed_kategorie'),
        ('packeta', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='PacketaProvizePolozka'),
            ],
            database_operations=[],
        ),
    ]
