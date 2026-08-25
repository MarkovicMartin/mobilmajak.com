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
    TYP_DPH_Z_FAKTURY = 'z_faktury'
    TYP_DPH_BEZ = 'bez'
    TYP_DPH_CHOICES = [
        (TYP_DPH_Z_FAKTURY, 'DPH z faktury'),
        (TYP_DPH_BEZ, 'Bez DPH'),
    ]

    nazev = models.CharField(max_length=120, unique=True)
    poradi = models.IntegerField(default=0)
    aktivni = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='deti',
    )
    typ_dph = models.CharField(
        max_length=20, choices=TYP_DPH_CHOICES,
        default=TYP_DPH_Z_FAKTURY, blank=True,
    )

    class Meta:
        db_table = 'finance_naklad_kategorie'
        ordering = ['poradi', 'nazev']
        verbose_name = 'Kategorie nákladu'
        verbose_name_plural = 'Kategorie nákladů'

    def __str__(self):
        return self.nazev


class FinanceDoklad(models.Model):
    STAV_CEKA_NA_OCR = 'ceka_na_ocr'
    STAV_KE_KONTROLE = 'ke_kontrole'
    STAV_SCHVALENO = 'schvaleno'
    STAV_ZAMITNUTO = 'zamitnuto'
    STAV_ODESLANO_FLEXI = 'odeslano_flexi'
    STAV_NOVA = 'nova'
    STAV_SPAROVANA = 'sparovana'
    STAV_CHOICES = [
        (STAV_CEKA_NA_OCR, 'Čeká na OCR'),
        (STAV_KE_KONTROLE, 'Ke kontrole'),
        (STAV_SCHVALENO, 'Schváleno'),
        (STAV_ZAMITNUTO, 'Zamítnuto'),
        (STAV_ODESLANO_FLEXI, 'Odesláno do Flexi'),
        (STAV_NOVA, 'Nová'),
        (STAV_SPAROVANA, 'Spárovaná'),
    ]

    MATCH_OK = 'ok'
    MATCH_WARN = 'warn'
    MATCH_FAIL = 'fail'
    MATCH_CHOICES = [
        (MATCH_OK, 'Sedí'),
        (MATCH_WARN, 'Kontrola'),
        (MATCH_FAIL, 'Nesedí'),
    ]

    soubor = models.CharField(max_length=500, blank=True, default='')
    dodavatel_nazev = models.CharField(max_length=200, blank=True, default='')
    dodavatel_ico = models.CharField(max_length=20, blank=True, default='')
    cislo_faktury = models.CharField(max_length=64, blank=True, default='')
    vs = models.CharField(max_length=32, blank=True, default='')
    datum_vystaveni = models.DateField(null=True, blank=True)
    datum_splatnosti = models.DateField(null=True, blank=True)
    castka_celkem = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    castka_bez_dph = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dph_castka = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dph_sazba = models.IntegerField(null=True, blank=True)
    stav = models.CharField(max_length=20, choices=STAV_CHOICES, default=STAV_CEKA_NA_OCR)
    match_stav = models.CharField(max_length=10, choices=MATCH_CHOICES, blank=True, default='')
    match_detail = models.JSONField(null=True, blank=True)
    schvalil_user_id = models.IntegerField(null=True, blank=True)
    schvaleno = SafeDateTimeField(null=True, blank=True)
    naklad_polozka = models.ForeignKey(
        'NakladPolozka', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='doklady',
    )
    ocr_raw = models.JSONField(null=True, blank=True)
    flexi_id = models.CharField(max_length=32, blank=True, default='', db_index=True)
    prirazeno_automaticky = models.BooleanField(default=False)
    vytvoreno = SafeDateTimeField(auto_now_add=True)
    upraveno = SafeDateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'finance_doklad'
        ordering = ['-vytvoreno']
        verbose_name = 'Finance doklad'
        verbose_name_plural = 'Finance doklady'


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
    ZDROJ_SYMPLIO_POKLADNA = 'symplio_pokladna'
    ZDROJ_CHOICES = [
        (ZDROJ_FIO, 'Fio'),
        (ZDROJ_MANUAL, 'Ruční'),
        (ZDROJ_SHEETS, 'Sheets import'),
        (ZDROJ_SYMPLIO_POKLADNA, 'Symplio pokladna'),
    ]

    DPH_STAV_CEKA = 'ceka_na_fakturu'
    DPH_STAV_SPAROVANO = 'sparovano'
    DPH_STAV_BEZ = 'bez_dph'
    DPH_STAV_CHOICES = [
        (DPH_STAV_CEKA, 'Čeká na fakturu'),
        (DPH_STAV_SPAROVANO, 'Spárováno'),
        (DPH_STAV_BEZ, 'Bez DPH'),
    ]

    TYP_PLATBY_ODCHOZI = 'odchozi'
    TYP_PLATBY_PRICHOZI = 'prichozi'
    TYP_PLATBY_INTERNI = 'interni'
    TYP_PLATBY_CHOICES = [
        (TYP_PLATBY_ODCHOZI, 'Odchozí'),
        (TYP_PLATBY_PRICHOZI, 'Příchozí'),
        (TYP_PLATBY_INTERNI, 'Interní'),
    ]

    datum = models.DateField()
    rok = models.IntegerField()
    mesic = models.IntegerField()
    castka = models.DecimalField(max_digits=12, decimal_places=2)
    castka_bez_dph = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dph_castka = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dph_sazba = models.IntegerField(null=True, blank=True)
    dph_stav = models.CharField(
        max_length=20, choices=DPH_STAV_CHOICES, default=DPH_STAV_CEKA,
    )
    typ_platby = models.CharField(
        max_length=20, choices=TYP_PLATBY_CHOICES, default=TYP_PLATBY_ODCHOZI,
    )
    kategorie = models.ForeignKey(
        NakladKategorie, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='polozky',
    )
    prodejna_id = models.IntegerField(null=True, blank=True)
    stav = models.CharField(max_length=20, choices=STAV_CHOICES, default=STAV_NEZARAZENO)
    zdroj = models.CharField(max_length=20, choices=ZDROJ_CHOICES, default=ZDROJ_MANUAL)
    fio_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    symplio_doklad = models.CharField(max_length=64, blank=True, default='')
    doklad = models.ForeignKey(
        FinanceDoklad, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='naklady',
    )
    popis = models.CharField(max_length=500, blank=True, default='')
    protiucet = models.CharField(max_length=64, blank=True, default='')
    vs = models.CharField(max_length=32, blank=True, default='')
    zprava = models.TextField(blank=True, default='')
    ignorovat = models.BooleanField(default=False)
    zarazeno_automaticky = models.BooleanField(default=False)
    auto_pravidlo = models.CharField(max_length=64, blank=True, default='')
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
            models.Index(fields=['dph_stav'], name='finance_nak_dph_sta_idx'),
        ]
        verbose_name = 'Položka nákladu'
        verbose_name_plural = 'Položky nákladů'


class FinanceZustatek(models.Model):
    TYP_FIO = 'fio'
    TYP_POKLADNA = 'pokladna'
    TYP_CHOICES = [
        (TYP_FIO, 'Fio účet'),
        (TYP_POKLADNA, 'Pokladna'),
    ]

    datum = models.DateField()
    typ = models.CharField(max_length=20, choices=TYP_CHOICES)
    label = models.CharField(max_length=64, blank=True, default='')
    prodejna_id = models.IntegerField(null=True, blank=True)
    castka = models.DecimalField(max_digits=14, decimal_places=2)
    mena = models.CharField(max_length=8, default='CZK')
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_zustatek'
        ordering = ['-datum', '-id']
        indexes = [
            models.Index(fields=['typ', 'datum'], name='finance_zus_typ_dat_idx'),
        ]
        verbose_name = 'Finance zůstatek'
        verbose_name_plural = 'Finance zůstatky'


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
