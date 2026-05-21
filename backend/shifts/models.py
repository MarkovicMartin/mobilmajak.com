from django.db import models
from users.models import WebUser

class Smena(models.Model):
    """Model pro směny prodejců"""
    
    TYP_SMENY = [
        ('prace', 'Práce'),
        ('dovolena', 'Dovolená'),
        ('nemoc', 'Nemocenská'),
    ]
    
    user = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='smeny')
    prodejna = models.ForeignKey('stores.Prodejna', on_delete=models.CASCADE, verbose_name="Prodejna", related_name='smeny')
    datum = models.DateField()
    cas_od = models.TimeField()
    cas_do = models.TimeField()
    typ_smeny = models.CharField(max_length=20, choices=TYP_SMENY, default='prace')
    poznamka = models.TextField(blank=True, null=True)
    aktivni = models.BooleanField(default=True)
    vytvoreno = models.DateTimeField(auto_now_add=True)
    upraveno = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'WEB_SMENY'
        verbose_name = 'Směna'
        verbose_name_plural = 'Směny'
        unique_together = ['user', 'datum', 'prodejna']  # Jeden prodejce může mít jen jednu směnu na prodejně za den
        ordering = ['-datum', 'cas_od']
    
    def __str__(self):
        return f"{self.user.prijmeni} - {self.prodejna} - {self.datum}"
    
    @property
    def je_domaci_prodejna(self):
        """Kontroluje, zda je směna na domácí prodejně prodejce"""
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
    cas = models.DateTimeField()
    poznamka = models.TextField(blank=True, null=True)
    vytvoreno = models.DateTimeField(auto_now_add=True)
    
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
    posledni_aktualizace = models.DateTimeField(auto_now=True)
    
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
    vytvoreno = models.DateTimeField(auto_now_add=True)
    upraveno = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_MZDOVAODMENA_MESIC'
        verbose_name = 'Měsíční odměna'
        verbose_name_plural = 'Měsíční odměny'
        unique_together = ['user', 'mesic']
        ordering = ['-mesic']

    def __str__(self):
        return f"{self.user_id} – {self.mesic.strftime('%m/%Y')}: {self.castka} bodů"
