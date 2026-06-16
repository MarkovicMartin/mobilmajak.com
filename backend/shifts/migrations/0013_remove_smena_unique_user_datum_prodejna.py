from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0012_alter_mzdovapenalizacemesic_id'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='smena',
            unique_together=set(),
        ),
    ]
