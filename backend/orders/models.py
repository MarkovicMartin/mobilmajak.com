from django.db import models
from users.models import WebUser


class Order(models.Model):
    """Model pro interní objednávky dílů"""
    
    STATUS_CHOICES = [
        ('nove', 'Nové'),
        ('v_kosiku', 'v košíku'),
        ('objednano', 'objednáno'),
        ('predobjednano', 'Předobjednáno'),  # legacy → sloupec objednáno
        ('neni_skladem', 'Není skladem'),  # filtr, ne hlavní sloupec
        ('storno', 'Storno'),  # filtr, ne hlavní sloupec
        ('dorazilo_ceka', 'připraveno'),  # DB klíč zachován (dříve „dorazilo čeká“)
        ('hotovo', 'vyřízeno'),
    ]
    
    # Informace o zákazníkovi
    jmeno_zakaznika = models.CharField(max_length=100, verbose_name="Jméno zákazníka")
    prijmeni_zakaznika = models.CharField(max_length=100, verbose_name="Příjmení zákazníka")
    telefon_zakaznika = models.CharField(max_length=20, verbose_name="Telefon zákazníka")
    
    # Informace o dílu
    typ_telefonu = models.CharField(max_length=100, verbose_name="Typ telefonu")
    dil = models.CharField(max_length=100, verbose_name="Díl")
    barva = models.CharField(max_length=50, blank=True, null=True, verbose_name="Barva")
    
    # Stav a workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nove', verbose_name="Stav")
    
    # Metadata
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_aktualizace = models.DateTimeField(auto_now=True, verbose_name="Datum aktualizace")
    
    # Kdo založil objednávku
    zalozil = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='zalozene_objednavky', verbose_name="Založil")
    
    # Kdo naposledy změnil stav
    posledni_zmena_uzivatel = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='zmenene_objednavky', verbose_name="Poslední změna uživatel")

    # Prodejna (auto ze směny / domovská)
    prodejna = models.ForeignKey(
        'stores.Prodejna',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='objednavky',
        verbose_name='Prodejna',
    )
    
    # Doplňující informace
    poznamka = models.TextField(blank=True, null=True, verbose_name="Poznámka")
    cena = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Cena")
    dodavatel = models.CharField(max_length=100, blank=True, null=True, verbose_name="Dodavatel")
    
    # Servisní číslo nebo číslo zákazníka (povinné při vytváření přes API)
    servisni_cislo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Servisní číslo")

    # Vazba na Symplio objednávku (O2)
    symplio_objednavka_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Symplio ID objednávky",
        help_text="ID v Symplio adminu (odkaz /admin/objednavky/objednavka-{id})",
    )

    # O3: čas poslední Slack SLA připomínky (reset při změně stavu)
    sla_reminder_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="SLA připomínka odeslána",
    )
    
    class Meta:
        db_table = 'WEB_OBJEDNAVKY'
        verbose_name = 'Objednávka'
        verbose_name_plural = 'Objednávky'
        ordering = ['-datum_vytvoreni']  # Nejnovější první
    
    def __str__(self):
        return f"{self.jmeno_zakaznika} {self.prijmeni_zakaznika} - {self.typ_telefonu} ({self.get_status_display()})"
    
    @property
    def celkova_doba_procesu(self):
        """Vypočítá celkovou dobu od vytvoření do dokončení"""
        if self.status in ['hotovo', 'storno']:
            posledni_zmena = self.historie_stavu.filter(novy_status=self.status).first()
            if posledni_zmena:
                return posledni_zmena.datum_zmeny - self.datum_vytvoreni
        return None

    @property
    def status_since(self):
        """Okamžik vstupu do aktuálního stavu (pro SLA)."""
        hist = self.historie_stavu.filter(novy_status=self.status).order_by('-datum_zmeny').first()
        if hist:
            return hist.datum_zmeny
        return self.datum_vytvoreni

    def days_in_current_status(self, now=None):
        from django.utils import timezone
        now = now or timezone.now()
        since = self.status_since
        if not since:
            return 0
        return max(0, (now - since).days)


class OrderStatusHistory(models.Model):
    """Historie změn stavů objednávek"""
    
    objednavka = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='historie_stavu', verbose_name="Objednávka")
    puvodni_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Původní stav")
    novy_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Nový stav")
    datum_zmeny = models.DateTimeField(auto_now_add=True, verbose_name="Datum změny")
    uzivatel = models.ForeignKey(WebUser, on_delete=models.CASCADE, verbose_name="Změnil uživatel")
    poznamka = models.TextField(blank=True, null=True, verbose_name="Poznámka ke změně")
    
    class Meta:
        db_table = 'WEB_OBJEDNAVKY_HISTORIE'
        verbose_name = 'Historie stavů objednávky'
        verbose_name_plural = 'Historie stavů objednávek'
        ordering = ['-datum_zmeny']
    
    def __str__(self):
        return f"{self.objednavka} - {self.puvodni_status} → {self.novy_status} ({self.uzivatel})"
    
    @property
    def doba_ve_stavu(self):
        """Vypočítá dobu kterou objednávka strávila v předchozím stavu"""
        predchozi_zmena = OrderStatusHistory.objects.filter(
            objednavka=self.objednavka,
            datum_zmeny__lt=self.datum_zmeny
        ).first()
        
        if predchozi_zmena:
            return self.datum_zmeny - predchozi_zmena.datum_zmeny
        else:
            # První změna - doba od vytvoření objednávky
            return self.datum_zmeny - self.objednavka.datum_vytvoreni 