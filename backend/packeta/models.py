from django.db import models

from users.fields import SafeDateTimeField


class PacketaProvizePolozka(models.Model):
    """Transakce z admin.packeta.com – návštěvy balíků na výdejním místě."""

    prodejna_id = models.IntegerField()
    cas = models.DateTimeField()
    zasilka = models.CharField(max_length=64)
    zasilka_raw = models.CharField(max_length=80, blank=True, default='')
    typ_provize = models.CharField(max_length=120)
    castka = models.DecimalField(max_digits=10, decimal_places=2)
    mena = models.CharField(max_length=8, default='Kč')
    poznamka = models.CharField(max_length=200, blank=True, default='')
    import_batch = models.CharField(max_length=64)
    id_prodejce = models.IntegerField(null=True, blank=True, db_index=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_packeta_provize'
        ordering = ['-cas']
        constraints = [
            models.UniqueConstraint(
                fields=['prodejna_id', 'zasilka', 'typ_provize', 'cas'],
                name='finance_packeta_uniq_row',
            ),
        ]
        indexes = [
            models.Index(fields=['prodejna_id', 'cas']),
            models.Index(fields=['zasilka']),
        ]
        verbose_name = 'Packeta provize'
        verbose_name_plural = 'Packeta provize položky'
