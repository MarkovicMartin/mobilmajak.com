from django.db import models
from users.fields import SafeDateTimeField
from users.models import WebUser

class Smena(models.Model):
    """Model pro směny prodejců"""
    
    TYP_SMENY = [
        ('prace', 'Práce'),
        ('dovolena', 'Dovolená'),
        ('nemoc', 'Nemocenská'),
    ]

    BRIGADNIK_REZIM = [
        ('prodejce', 'Jako prodejce'),
        ('vypomoc', 'Výpomoc'),
    ]

    POZICE_SMENY = [
        ('prodej', 'Prodej'),
        ('servis', 'Servisní technik'),
        ('backoffice', 'Backoffice'),
    ]
    
    user = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='smeny')
    prodejna = models.ForeignKey(
        'stores.Prodejna',
        on_delete=models.CASCADE,
        verbose_name="Prodejna",
        related_name='smeny',
        null=True,
        blank=True,
    )
    datum = models.DateField()
    cas_od = models.TimeField()
    cas_do = models.TimeField()
    typ_smeny = models.CharField(max_length=20, choices=TYP_SMENY, default='prace')
    brigadnik_rezim = models.CharField(
        max_length=20,
        choices=BRIGADNIK_REZIM,
        default='prodejce',
        blank=True,
        verbose_name='Režim brigádníka',
        help_text='Výpomoc: 150 bodů/h bez provize. Jako prodejce: sazba z profilu + provize.',
    )
    pozice_smeny = models.CharField(
        max_length=20,
        choices=POZICE_SMENY,
        default='prodej',
        blank=True,
        verbose_name='Pozice na směně',
    )
    poznamka = models.TextField(blank=True, null=True)
    aktivni = models.BooleanField(default=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)
    upraveno = SafeDateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'WEB_SMENY'
        verbose_name = 'Směna'
        verbose_name_plural = 'Směny'
        ordering = ['-datum', 'cas_od']
    
    def __str__(self):
        store = self.prodejna or '—'
        return f"{self.user.prijmeni} - {store} - {self.datum}"

    @property
    def je_absence(self):
        return self.typ_smeny in ('dovolena', 'nemoc')

    @property
    def je_domaci_prodejna(self):
        """Kontroluje, zda je směna na domácí prodejně prodejce"""
        if not self.prodejna_id:
            return True
        return self.prodejna.id == self.user.prodejna_id
    
    @property
    def delka_smeny_hodin(self):
        """Vypočítá délku směny v hodinách"""
        if self.typ_smeny != 'prace':
            return 0
        
        from datetime import datetime, timedelta
        cas_od_dt = datetime.combine(self.datum, self.cas_od)
        cas_do_dt = datetime.combine(self.datum, self.cas_do)
        
        # Pokud končí později než začíná (přes půlnoc)
        if cas_do_dt < cas_od_dt:
            cas_do_dt += timedelta(days=1)
        
        rozdil = cas_do_dt - cas_od_dt
        return round(rozdil.total_seconds() / 3600, 2)


class SmenaDochazka(models.Model):
    """Model pro evidenci docházky - check-in/out/pauzy"""
    
    TYP_AKCE = [
        ('prichod', 'Příchod'),
        ('odchod', 'Odchod'),
        ('pauza_start', 'Začátek pauzy'),
        ('pauza_konec', 'Konec pauzy'),
    ]
    
    smena = models.ForeignKey(Smena, on_delete=models.CASCADE, related_name='dochazka')
    typ_akce = models.CharField(max_length=20, choices=TYP_AKCE)
    cas = SafeDateTimeField()
    poznamka = models.TextField(blank=True, null=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'WEB_SMENY_DOCHAZKA'
        verbose_name = 'Docházka'
        verbose_name_plural = 'Docházka'
        ordering = ['cas']
    
    def __str__(self):
        return f"{self.smena.user.prijmeni} - {self.get_typ_akce_display()} - {self.cas.strftime('%H:%M')}"


class SmenaStatistiky(models.Model):
    """Model pro měsíční statistiky směn (pro rychlejší načítání)"""
    
    user = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='smena_statistiky')
    mesic = models.DateField()  # První den měsíce
    pocet_hodin_naplanovanych = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pocet_hodin_odpracovanych = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pocet_hodin_dovolene = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pocet_hodin_pauz = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pocet_presasu = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    posledni_aktualizace = SafeDateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'WEB_SMENY_STATISTIKY'
        verbose_name = 'Statistiky směn'
        verbose_name_plural = 'Statistiky směn'
        unique_together = ['user', 'mesic']
        ordering = ['-mesic']
    
    def __str__(self):
        return f"{self.user.prijmeni} - {self.mesic.strftime('%m/%Y')}"


class MzdovaOdmenaMesic(models.Model):
    """Měsíční variabilní odměna přiřazená administrátorem (body)."""

    user = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='mzda_odmeny_mesic')
    mesic = models.DateField(verbose_name="Měsíc (první den)")
    castka = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Odměna (body)")
    poznamka = models.TextField(blank=True, null=True)
    vytvoreno = SafeDateTimeField(auto_now_add=True)
    upraveno = SafeDateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_MZDOVAODMENA_MESIC'
        verbose_name = 'Měsíční odměna'
        verbose_name_plural = 'Měsíční odměny'
        unique_together = ['user', 'mesic']
        ordering = ['-mesic']

    def __str__(self):
        return f"{self.user_id} – {self.mesic.strftime('%m/%Y')}: {self.castka} bodů"


class MzdovaPenalizaceMesic(models.Model):
    """Srážka z provize za měsíc – procenta z hrubé provize nebo fixní body."""

    TYP_PROCENTA = 'procenta'
    TYP_FIXNI = 'fixni'
    TYP_CHOICES = [
        (TYP_PROCENTA, 'Procenta z provize'),
        (TYP_FIXNI, 'Fixní body'),
    ]

    user = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='mzda_penalizace_mesic')
    mesic = models.DateField(verbose_name="Měsíc (první den)")
    duvod = models.TextField(verbose_name="Důvod srážky")
    typ = models.CharField(
        max_length=16,
        choices=TYP_CHOICES,
        default=TYP_PROCENTA,
        verbose_name="Typ srážky",
    )
    hodnota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10,
        verbose_name="Hodnota (%, nebo body)",
    )
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'WEB_MZDOVA_PENALIZACE_MESIC'
        verbose_name = 'Měsíční penalizace'
        verbose_name_plural = 'Měsíční penalizace'
        ordering = ['mesic', 'vytvoreno']

    def __str__(self):
        if self.typ == self.TYP_FIXNI:
            return f"{self.user_id} – {self.mesic.strftime('%m/%Y')}: −{self.hodnota} b ({self.duvod[:40]})"
        return f"{self.user_id} – {self.mesic.strftime('%m/%Y')}: −{self.hodnota} % ({self.duvod[:40]})"


class ProdejnaPohybUdalost(models.Model):
    """Pilot: signál pohyb / klid z brány v LAN (bez uložení obrazu)."""

    prodejna = models.ForeignKey(
        'stores.Prodejna',
        on_delete=models.CASCADE,
        related_name='pohyb_udalosti',
    )
    pohyb = models.BooleanField(verbose_name='Detekován pohyb')
    cas = SafeDateTimeField(db_index=True)
    zdroj = models.CharField(max_length=32, default='gateway')
    vytvoreno = SafeDateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'WEB_PRODEJNA_POHYB_UDALOST'
        verbose_name = 'Pohyb na prodejně'
        verbose_name_plural = 'Pohyb na prodejnách'
        ordering = ['-cas']
        indexes = [
            models.Index(fields=['prodejna', '-cas'], name='idx_pohyb_prodejna_cas'),
        ]

    def __str__(self):
        st = 'pohyb' if self.pohyb else 'klid'
        return f'{self.prodejna_id} – {st} – {self.cas}'
