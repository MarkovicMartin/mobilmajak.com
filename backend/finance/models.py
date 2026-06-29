from django.db import models

from users.fields import SafeDateTimeField


class FinanceAuditLog(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    akce = models.CharField(max_length=100)
    detail = models.TextField(blank=True, default='')
    ip = models.CharField(max_length=64, blank=True, default='')
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_audit_log'
        ordering = ['-vytvoreno']
        verbose_name = 'Finance audit log'
        verbose_name_plural = 'Finance audit logy'


class NakladKategorie(models.Model):
    nazev = models.CharField(max_length=120, unique=True)
    poradi = models.IntegerField(default=0)
    aktivni = models.BooleanField(default=True)

    class Meta:
        db_table = 'finance_naklad_kategorie'
        ordering = ['poradi', 'nazev']
        verbose_name = 'Kategorie nákladu'
        verbose_name_plural = 'Kategorie nákladů'

    def __str__(self):
        return self.nazev


class NakladPolozka(models.Model):
    STAV_ZARAZENO = 'zarazeno'
    STAV_NEZARAZENO = 'nezarazeno'
    STAV_IGNOROVAT = 'ignorovat'
    STAV_RUCNE = 'rucne_upraveno'
    STAV_CHOICES = [
        (STAV_ZARAZENO, 'Zařazeno'),
        (STAV_NEZARAZENO, 'Nezařazeno'),
        (STAV_IGNOROVAT, 'Ignorovat'),
        (STAV_RUCNE, 'Ručně upraveno'),
    ]

    ZDROJ_FIO = 'fio'
    ZDROJ_MANUAL = 'manual'
    ZDROJ_SHEETS = 'sheets_import'
    ZDROJ_CHOICES = [
        (ZDROJ_FIO, 'Fio'),
        (ZDROJ_MANUAL, 'Ruční'),
        (ZDROJ_SHEETS, 'Sheets import'),
    ]

    datum = models.DateField()
    rok = models.IntegerField()
    mesic = models.IntegerField()
    castka = models.DecimalField(max_digits=12, decimal_places=2)
    kategorie = models.ForeignKey(
        NakladKategorie, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='polozky',
    )
    prodejna_id = models.IntegerField(null=True, blank=True)
    stav = models.CharField(max_length=20, choices=STAV_CHOICES, default=STAV_NEZARAZENO)
    zdroj = models.CharField(max_length=20, choices=ZDROJ_CHOICES, default=ZDROJ_MANUAL)
    fio_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    popis = models.CharField(max_length=500, blank=True, default='')
    protiucet = models.CharField(max_length=64, blank=True, default='')
    vs = models.CharField(max_length=32, blank=True, default='')
    zprava = models.TextField(blank=True, default='')
    ignorovat = models.BooleanField(default=False)
    zarazeno_automaticky = models.BooleanField(default=False)
    poznamka_admin = models.TextField(blank=True, default='')
    upravil_user_id = models.IntegerField(null=True, blank=True)
    upraveno = SafeDateTimeField(null=True, blank=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_naklad_polozka'
        ordering = ['-datum', '-id']
        indexes = [
            models.Index(fields=['stav', 'datum']),
            models.Index(fields=['rok', 'mesic']),
        ]
        verbose_name = 'Položka nákladu'
        verbose_name_plural = 'Položky nákladů'


class FioKategorizacniPravidlo(models.Model):
    protiucet = models.CharField(max_length=64, blank=True, default='')
    zprava_obsahuje = models.CharField(max_length=200, blank=True, default='')
    vs = models.CharField(max_length=32, blank=True, default='')
    castka_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    castka_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    kategorie = models.ForeignKey(
        NakladKategorie, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='fio_pravidla',
    )
    prodejna_id = models.IntegerField(null=True, blank=True)
    ignorovat = models.BooleanField(default=False)
    aktivni = models.BooleanField(default=True)
    vytvoril_user_id = models.IntegerField(null=True, blank=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_fio_pravidlo'
        ordering = ['-id']
        verbose_name = 'Fio kategorizační pravidlo'
        verbose_name_plural = 'Fio kategorizační pravidla'


class PacketaProvizePolozka(models.Model):
    prodejna_id = models.IntegerField()
    cas = models.DateTimeField()
    zasilka = models.CharField(max_length=64)
    zasilka_raw = models.CharField(max_length=80, blank=True, default='')
    typ_provize = models.CharField(max_length=120)
    castka = models.DecimalField(max_digits=10, decimal_places=2)
    mena = models.CharField(max_length=8, default='Kč')
    poznamka = models.CharField(max_length=200, blank=True, default='')
    import_batch = models.CharField(max_length=64)
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
