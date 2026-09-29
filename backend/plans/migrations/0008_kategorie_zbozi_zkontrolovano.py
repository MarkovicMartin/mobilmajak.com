from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0007_kategorie_zbozi_prepsano'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategoriezboziclaim',
            name='zkontrolovano',
            field=models.BooleanField(default=False, verbose_name='Admin zkontroloval zařazení'),
        ),
        migrations.AddField(
            model_name='kategoriezboziclaim',
            name='zkontrolovano_kdy',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
