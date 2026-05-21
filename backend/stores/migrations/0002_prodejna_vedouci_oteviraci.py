from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='prodejna',
            name='oteviraci_doba',
            field=models.JSONField(blank=True, default=dict, verbose_name='Otevírací doba Po–Ne (JSON)'),
        ),
        migrations.AddField(
            model_name='prodejna',
            name='vedouci_user_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='ID vedoucího (WebUser)'),
        ),
    ]
