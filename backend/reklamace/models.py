from datetime import timedelta

from django.db import models
from django.utils import timezone


class ReklamaceStatus(models.TextChoices):
    NEZPRACOVANE = 'nezpracovane', 'Nezpracované'
    ODESLANE = 'odeslane', 'Odeslané'
    VRIZENE = 'vyrizene', 'Vyřízené'


class ZpusobVyrizeni(models.TextChoices):
    VYMENA = 'vymena', 'Výměna'
    DOBROPIS = 'dobropis', 'Dobropis'
    OPRAVA = 'oprava', 'Oprava'
    ZAMITNUTO = 'zamitnuto', 'Zamítnuto'
    JINE = 'jine', 'Jiné'


OVERDUE_HOURS = 24


class ReklamacePolozka(models.Model):
    """Evidence odeslaných reklamací dílů (náhrada za Excel listy Servis Reklamace)."""

    nase_znacka = models.CharField(max_length=20, verbose_name='Naše značka')
    jejich_oznaceni = models.CharField(max_length=100, blank=True, default='', verbose_name='Jejich označení')
    nazev_zbozi = models.CharField(max_length=300, verbose_name='Název zboží')
    dodavatel = models.CharField(max_length=100, blank=True, default='', verbose_name='Dodavatel')
    faktura = models.CharField(max_length=50, blank=True, default='', verbose_name='Faktura')
    ean = models.CharField(max_length=50, blank=True, default='', verbose_name='EAN')
    p_kod = models.CharField(max_length=50, blank=True, default='', verbose_name='P kód')
    datum_odeslani = models.DateField(null=True, blank=True, verbose_name='Datum odeslání')
    cislo_zasilky = models.CharField(max_length=100, blank=True, default='', verbose_name='Číslo zásilky')
    poznamka = models.TextField(blank=True, default='', verbose_name='Poznámka')
    prodejna = models.CharField(max_length=100, verbose_name='Prodejna')
    status = models.CharField(
        max_length=20,
        choices=ReklamaceStatus.choices,
        default=ReklamaceStatus.NEZPRACOVANE,
        verbose_name='Stav',
    )
    datum_vyrizeni = models.DateField(null=True, blank=True, verbose_name='Datum vyřízení')
    zpusob_vyrizeni = models.CharField(
        max_length=20,
        choices=ZpusobVyrizeni.choices,
        blank=True,
        default='',
        verbose_name='Způsob vyřízení',
    )
    odeslano_dodavateli_at = models.DateTimeField(null=True, blank=True, verbose_name='Odesláno dodavateli')
    sklad_vyskladneno = models.BooleanField(default=False, verbose_name='Vyskladněno')
    sklad_naskladneno = models.BooleanField(default=False, verbose_name='Naskladněno')
    is_active = models.BooleanField(default=True, verbose_name='Aktivní')
    created_by = models.ForeignKey(
        'users.WebUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reklamace_vytvorene',
        verbose_name='Založil',
    )
    reminder_10d_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Odeslána 10d připomínka',
    )
    reminder_30d_slack_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Odeslána 30d Slack připomínka',
    )
    reminder_tracking_2d_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Odeslána 2d připomínka čísla balíčku',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_REKLAMACE_EVIDENCE'
        verbose_name = 'Reklamace položka'
        verbose_name_plural = 'Reklamace evidence'
        ordering = ['-datum_odeslani', '-nase_znacka']

    def __str__(self):
        return f'{self.nase_znacka} – {self.nazev_zbozi}'

    @property
    def is_overdue(self):
        if self.status != ReklamaceStatus.NEZPRACOVANE:
            return False
        return timezone.now() - self.created_at > timedelta(hours=OVERDUE_HOURS)


class ReklamaceNotifikace(models.Model):
    """In-app připomínka k reklamaci (např. 10 dní od založení)."""

    reklamace = models.ForeignKey(
        ReklamacePolozka,
        on_delete=models.CASCADE,
        related_name='notifikace',
        verbose_name='Reklamace',
    )
    user = models.ForeignKey(
        'users.WebUser',
        on_delete=models.CASCADE,
        related_name='reklamace_notifikace',
        verbose_name='Uživatel',
    )
    message = models.CharField(max_length=300, verbose_name='Zpráva')
    typ = models.CharField(max_length=30, default='reminder_10d', verbose_name='Typ')
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Přečteno')

    class Meta:
        db_table = 'WEB_REKLAMACE_NOTIFIKACE'
        verbose_name = 'Reklamace notifikace'
        verbose_name_plural = 'Reklamace notifikace'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.typ} → user #{self.user_id}'
