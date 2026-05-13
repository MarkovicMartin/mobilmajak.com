from django.db import models
from django.utils import timezone
from datetime import date


class BaseProdejniData(models.Model):
    """Abstraktní model pro společná pole denních a měsíčních dat"""
    
    # Metadata
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Prodejní informace
    prodejna = models.CharField(max_length=100)
    prodejce = models.CharField(max_length=100)
    id_prodejce = models.IntegerField(null=True, blank=True)
    
    # Klíčové metriky
    polozky_nad_100 = models.IntegerField(default=0)
    sluzby_celkem = models.IntegerField(default=0)
    pol_dok = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # průměr položek na účtenku
    
    # Produkty
    ct300 = models.IntegerField(default=0)
    ct600 = models.IntegerField(default=0)
    ct1200 = models.IntegerField(default=0)
    akt = models.IntegerField(default=0)
    zah250 = models.IntegerField(default=0)
    nap = models.IntegerField(default=0)
    zah500 = models.IntegerField(default=0)
    kop250 = models.IntegerField(default=0)
    kop500 = models.IntegerField(default=0)
    pz1 = models.IntegerField(default=0)
    knz = models.IntegerField(default=0)
    aligator = models.IntegerField(default=0)
    
    class Meta:
        abstract = True
        ordering = ['-timestamp', 'prodejna', 'prodejce']


def get_current_year():
    return date.today().year

def get_current_month():
    return date.today().month


class ProdejniDataDenni(models.Model):
    """Denní prodejní data pro jednotlivé uživatele (STARÝ MODEL - DEPRECATED)"""
    
    uzivatel = models.ForeignKey('users.WebUser', on_delete=models.CASCADE, verbose_name="Uživatel", null=True, blank=True)
    datum = models.DateField(verbose_name="Datum", default=date.today)
    
    # Základní metriky
    polozky_nad_100 = models.IntegerField(default=0, verbose_name="Položky nad 100 Kč")
    sluzby_celkem = models.IntegerField(default=0, verbose_name="Služby celkem")
    prumer_polozek_uctu = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Průměr položek/účtu")
    
    # Produkty
    ct300 = models.IntegerField(default=0, verbose_name="CT300")
    ct600 = models.IntegerField(default=0, verbose_name="CT600")
    ct1200 = models.IntegerField(default=0, verbose_name="CT1200")
    akt = models.IntegerField(default=0, verbose_name="AKT")
    zah250 = models.IntegerField(default=0, verbose_name="ZAH250")
    nap = models.IntegerField(default=0, verbose_name="NAP")
    zah500 = models.IntegerField(default=0, verbose_name="ZAH500")
    kop250 = models.IntegerField(default=0, verbose_name="KOP250")
    kop500 = models.IntegerField(default=0, verbose_name="KOP500")
    pz1 = models.IntegerField(default=0, verbose_name="PZ1")
    knz = models.IntegerField(default=0, verbose_name="KNZ")
    aligator = models.IntegerField(default=0, verbose_name="ALIGATOR")
    
    # Časové údaje
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_upravy = models.DateTimeField(auto_now=True, verbose_name="Datum úpravy")
    
    class Meta:
        db_table = 'WEB_ANALYTICS_PRODEJNIDATADENNI'
        verbose_name = "Denní prodejní data (deprecated)"
        verbose_name_plural = "Denní prodejní data (deprecated)"
        unique_together = ['uzivatel', 'datum']
    
    def __str__(self):
        return f"{self.uzivatel.uzivatelske_jmeno if self.uzivatel else 'Neznámý'} - {self.datum}"


class ProdejniDataMesicni(models.Model):
    """Měsíční prodejní data pro jednotlivé uživatele (STARÝ MODEL - DEPRECATED)"""
    
    uzivatel = models.ForeignKey('users.WebUser', on_delete=models.CASCADE, verbose_name="Uživatel", null=True, blank=True)
    rok = models.IntegerField(verbose_name="Rok", default=get_current_year)
    mesic = models.IntegerField(verbose_name="Měsíc", default=get_current_month)
    
    # Základní metriky
    polozky_nad_100 = models.IntegerField(default=0, verbose_name="Položky nad 100 Kč")
    sluzby_celkem = models.IntegerField(default=0, verbose_name="Služby celkem")
    prumer_polozek_uctu = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Průměr položek/účtu")
    
    # Produkty
    ct300 = models.IntegerField(default=0, verbose_name="CT300")
    ct600 = models.IntegerField(default=0, verbose_name="CT600")
    ct1200 = models.IntegerField(default=0, verbose_name="CT1200")
    akt = models.IntegerField(default=0, verbose_name="AKT")
    zah250 = models.IntegerField(default=0, verbose_name="ZAH250")
    nap = models.IntegerField(default=0, verbose_name="NAP")
    zah500 = models.IntegerField(default=0, verbose_name="ZAH500")
    kop250 = models.IntegerField(default=0, verbose_name="KOP250")
    kop500 = models.IntegerField(default=0, verbose_name="KOP500")
    pz1 = models.IntegerField(default=0, verbose_name="PZ1")
    knz = models.IntegerField(default=0, verbose_name="KNZ")
    aligator = models.IntegerField(default=0, verbose_name="ALIGATOR")
    
    # Časové údaje
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_upravy = models.DateTimeField(auto_now=True, verbose_name="Datum úpravy")
    
    class Meta:
        db_table = 'WEB_ANALYTICS_PRODEJNIDATAMESICNI'
        verbose_name = "Měsíční prodejní data (deprecated)"
        verbose_name_plural = "Měsíční prodejní data (deprecated)"
        unique_together = ['uzivatel', 'rok', 'mesic']
    
    def __str__(self):
        return f"{self.uzivatel.uzivatelske_jmeno if self.uzivatel else 'Neznámý'} - {self.rok}/{self.mesic:02d}"


# NOVÉ MODELY PRO APIFY TABULKY
# =============================

class PolozkyDenni(models.Model):
    """Denní prodejní data z Apify - nový model"""
    
    # Základní identifikace
    prodejce = models.CharField(max_length=100, verbose_name="Prodejce")
    id_prodejce = models.IntegerField(verbose_name="ID Prodejce")
    prodejna = models.CharField(max_length=100, null=True, blank=True, verbose_name="Prodejna")
    id_prodejna = models.IntegerField(null=True, blank=True, verbose_name="ID Prodejny")
    
    # Základní metriky
    nad_100 = models.IntegerField(default=0, verbose_name="Položky nad 100 Kč")
    sluzby = models.IntegerField(default=0, verbose_name="Služby celkem")
    pol_dok = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Průměr položek/účtu")
    
    # Produkty
    ct300 = models.IntegerField(default=0, verbose_name="CT300")
    ct600 = models.IntegerField(default=0, verbose_name="CT600")
    ct1200 = models.IntegerField(default=0, verbose_name="CT1200")
    akt = models.IntegerField(default=0, verbose_name="AKT")
    zah250 = models.IntegerField(default=0, verbose_name="ZAH250")
    nap = models.IntegerField(default=0, verbose_name="NAP")
    zah500 = models.IntegerField(default=0, verbose_name="ZAH500")
    kop250 = models.IntegerField(default=0, verbose_name="KOP250")
    kop500 = models.IntegerField(default=0, verbose_name="KOP500")
    pz1 = models.IntegerField(default=0, verbose_name="PZ1")
    knz = models.IntegerField(default=0, verbose_name="KNZ")
    
    # Časové údaje
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    datum = models.DateField(verbose_name="Datum")
    
    class Meta:
        db_table = 'WEB_POLOZKY_DENNI'
        verbose_name = "Denní položky (Apify)"
        verbose_name_plural = "Denní položky (Apify)"
        ordering = ['-datum', '-timestamp']
        indexes = [
            models.Index(fields=['id_prodejce', 'datum']),
            models.Index(fields=['datum']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.prodejce} - {self.prodejna} - {self.datum}"
    
    @property
    def polozky_nad_100(self):
        """Kompatibilita se starým API"""
        return self.nad_100
    
    @property
    def sluzby_celkem(self):
        """Kompatibilita se starým API"""
        return self.sluzby
    
    @property
    def prumer_polozek_uctu(self):
        """Kompatibilita se starým API"""
        return self.pol_dok
    
    @property
    def aligator(self):
        """Kompatibilita se starým API - Apify tabulky nemají aligator"""
        return 0


class PolozkyMesicni(models.Model):
    """Měsíční prodejní data z Apify - nový model"""
    
    # Základní identifikace
    prodejce = models.CharField(max_length=100, verbose_name="Prodejce")
    id_prodejce = models.IntegerField(verbose_name="ID Prodejce")
    prodejna = models.CharField(max_length=100, null=True, blank=True, verbose_name="Prodejna")
    id_prodejna = models.IntegerField(null=True, blank=True, verbose_name="ID Prodejny")
    
    # Základní metriky
    nad_100 = models.IntegerField(default=0, verbose_name="Položky nad 100 Kč")
    sluzby = models.IntegerField(default=0, verbose_name="Služby celkem")
    pol_dok = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Průměr položek/účtu")
    
    # Produkty
    ct300 = models.IntegerField(default=0, verbose_name="CT300")
    ct600 = models.IntegerField(default=0, verbose_name="CT600")
    ct1200 = models.IntegerField(default=0, verbose_name="CT1200")
    akt = models.IntegerField(default=0, verbose_name="AKT")
    zah250 = models.IntegerField(default=0, verbose_name="ZAH250")
    nap = models.IntegerField(default=0, verbose_name="NAP")
    zah500 = models.IntegerField(default=0, verbose_name="ZAH500")
    kop250 = models.IntegerField(default=0, verbose_name="KOP250")
    kop500 = models.IntegerField(default=0, verbose_name="KOP500")
    pz1 = models.IntegerField(default=0, verbose_name="PZ1")
    knz = models.IntegerField(default=0, verbose_name="KNZ")
    
    # Časové údaje
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    mesic_rok = models.CharField(max_length=7, verbose_name="Měsíc-Rok")  # Format: "2025-07"
    
    class Meta:
        db_table = 'WEB_POLOZKY_MESICNI'
        verbose_name = "Měsíční položky (Apify)"
        verbose_name_plural = "Měsíční položky (Apify)"
        ordering = ['-mesic_rok', '-timestamp']
        indexes = [
            models.Index(fields=['id_prodejce', 'mesic_rok']),
            models.Index(fields=['mesic_rok']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.prodejce} - {self.prodejna} - {self.mesic_rok}"
    
    @property
    def polozky_nad_100(self):
        """Kompatibilita se starým API"""
        return self.nad_100
    
    @property
    def sluzby_celkem(self):
        """Kompatibilita se starým API"""
        return self.sluzby
    
    @property
    def prumer_polozek_uctu(self):
        """Kompatibilita se starým API"""
        return self.pol_dok
    
    @property
    def aligator(self):
        """Kompatibilita se starým API - Apify tabulky nemají aligator"""
        return 0
    
    @property
    def rok(self):
        """Extrahuje rok z mesic_rok pole"""
        if self.mesic_rok:
            return int(self.mesic_rok.split('-')[0])
        return None
    
    @property
    def mesic(self):
        """Extrahuje měsíc z mesic_rok pole"""
        if self.mesic_rok:
            return int(self.mesic_rok.split('-')[1])
        return None


# Zachováváme starý model pro zpětnou kompatibilitu (označený jako deprecated)
class ProdejniData(BaseProdejniData):
    """DEPRECATED: Původní model - používejte PolozkyDenni nebo PolozkyMesicni"""
    
    DATA_TYPE_CHOICES = [
        ('daily', 'Denní data'),
        ('monthly', 'Měsíční data'),
    ]
    
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES, default='daily')
    
    class Meta:
        db_table = 'WEB_PRODEJNI_DATA'
        verbose_name = 'Prodejní data (deprecated)'
        verbose_name_plural = 'Prodejní data (deprecated)'
        ordering = ['-timestamp', 'prodejna', 'prodejce']
    
    def __str__(self):
        return f"OLD: {self.prodejna} - {self.prodejce} ({self.data_type}) - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"


class GoogleSheetsConfig(models.Model):
    """Konfigurace pro připojení k Google Sheets (DEPRECATED - už se nepoužívá)"""
    
    name = models.CharField(max_length=100, unique=True)
    spreadsheet_id = models.CharField(max_length=200)
    daily_sheet_name = models.CharField(max_length=100, default='List 1')
    monthly_sheet_name = models.CharField(max_length=100, default='od 1')
    api_key = models.TextField(blank=True)  # Pro uložení API credentials
    is_active = models.BooleanField(default=False)  # Deaktivováno
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'WEB_GOOGLE_SHEETS_CONFIG'
        verbose_name = 'Google Sheets konfigurace (deprecated)'
        verbose_name_plural = 'Google Sheets konfigurace (deprecated)'
    
    def __str__(self):
        return f"Google Sheets: {self.name} (deprecated)" 


class WebProdeje(models.Model):
    """
    Model pro tabulku WEB_PRODEJE - kompletní prodejní data firmy
    Obsahuje všechny prodané položky od 1.1.2025 do současnosti
    """
    
    # Základní identifikace
    id = models.AutoField(primary_key=True)
    typ = models.CharField(max_length=100, null=True, blank=True, verbose_name="Datum prodeje", db_column='Vystaveno')  # Datum kdy se položka prodala
    kod = models.CharField(max_length=100, null=True, blank=True, verbose_name="Kód položky", db_column='Kod')
    nazev = models.TextField(null=True, blank=True, verbose_name="Název položky", db_column='Nazev')
    
    # Doklad
    doklad = models.CharField(max_length=100, null=True, blank=True, verbose_name="Číslo účtenky/faktury", db_column='Doklad')
    nazev_dokladu = models.CharField(max_length=255, null=True, blank=True, verbose_name="Název dokladu", db_column='Nazev_dokladu')
    objednavka = models.CharField(max_length=100, null=True, blank=True, verbose_name="Číslo objednávky", db_column='Objednavka')
    
    # Místo prodeje a personál
    polozka = models.CharField(max_length=100, null=True, blank=True, verbose_name="Položka dokladu", db_column='Polozka')
    stredisko = models.CharField(max_length=100, null=True, blank=True, verbose_name="Název prodejny", db_column='Stredisko')
    spravce = models.CharField(max_length=100, null=True, blank=True, verbose_name="Správce", db_column='Spravce')
    
    # Poznámky
    poznamka = models.TextField(null=True, blank=True, verbose_name="Poznámka k položce", db_column='Poznamka')
    poznamka_dokladu = models.TextField(null=True, blank=True, verbose_name="Poznámka k dokladu", db_column='Poznamka_dokladu')
    
    # Množství a ceny
    pocet_kusu = models.IntegerField(null=True, blank=True, verbose_name="Počet kusů", db_column='Pocet_kusu')
    cena_ks_vcl_dph = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Prodejní cena s DPH", db_column='Cena_ks_vcl_DPH')
    skladova_cena_bez_dph = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Nákupní cena bez DPH", db_column='Skladova_cena_bez_DPH')
    skladova_cena_bez_dph_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Celková nákupní cena", db_column='Skladova_cena_bez_DPH_total')
    
    # Prodejní kanály
    marketingovy_kanal = models.CharField(max_length=100, null=True, blank=True, verbose_name="Marketing kanál", db_column='Marketingovy_kanal')  # e-shop vs prodejna
    dropshipping = models.CharField(max_length=10, null=True, blank=True, verbose_name="Dropshipping", db_column='Dropshipping')  # Baselinker = ALLEGRO
    
    # Identifikátory
    id_prodejce = models.IntegerField(null=True, blank=True, verbose_name="ID prodejce", db_column='ID_PRODEJCE')
    id_prodejny = models.IntegerField(null=True, blank=True, verbose_name="ID prodejny", db_column='ID_PRODEJNY')
    
    # Zisk
    zisk = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Zisk", db_column='ZISK')
    
    # Kategorie produktů
    kategorie = models.CharField(max_length=255, null=True, blank=True, verbose_name="Hlavní kategorie", db_column='KATEGORIE')
    kategorie_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Podkategorie 1", db_column='KATEGORIE_1')
    kategorie_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Podkategorie 2", db_column='KATEGORIE_2')
    
    # Metadata
    datum_vlozeni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vložení do DB", db_column='datum_vlozeni')
    
    class Meta:
        db_table = 'WEB_PRODEJE'
        verbose_name = 'Prodejní položka'
        verbose_name_plural = 'Prodejní položky'
        ordering = ['-datum_vlozeni', '-id']
        indexes = [
            models.Index(fields=['typ'], name='idx_prodeje_typ'),
            models.Index(fields=['id_prodejce'], name='idx_prodeje_prodejce'),
            models.Index(fields=['id_prodejny'], name='idx_prodeje_prodejny'),
            models.Index(fields=['marketingovy_kanal'], name='idx_prodeje_kanal'),
            models.Index(fields=['kategorie'], name='idx_prodeje_kategorie'),
            models.Index(fields=['stredisko'], name='idx_prodeje_stredisko'),
        ]
    
    def __str__(self):
        return f"{self.typ} - {self.nazev} ({self.cena_ks_vcl_dph} Kč)"
    
    @property
    def je_eshop(self):
        """Vrací True pokud se jedná o prodej z e-shopu"""
        return self.marketingovy_kanal == 'e-shop'
    
    @property
    def je_allegro(self):
        """Vrací True pokud se jedná o prodej z ALLEGRO"""
        return self.dropshipping == 'Baselinker'
    
    @property
    def je_servis(self):
        """Vrací True pokud se jedná o servisní službu"""
        return self.kategorie and '!Servis' in self.kategorie
    
    @property
    def celkova_cena(self):
        """Celková prodejní cena (počet kusů × cena za kus)"""
        if self.pocet_kusu and self.cena_ks_vcl_dph:
            return self.pocet_kusu * self.cena_ks_vcl_dph
        return self.cena_ks_vcl_dph or 0
    
    @property
    def celkovy_zisk(self):
        """Celkový zisk (počet kusů × zisk za kus)"""
        if self.pocet_kusu and self.zisk:
            return self.pocet_kusu * self.zisk
        return self.zisk or 0


from django.db import models
from django.utils import timezone

class WebProdejeAll(models.Model):
    """
    Model pro tabulku WEB_PRODEJE_ALL - rozšířená verze prodejních dat
    Obsahuje všechny prodané položky s dodatečnými analýzami a agregacemi
    """
    
    # Základní identifikace (stejné jako WEB_PRODEJE)
    id = models.AutoField(primary_key=True)
    typ = models.DateField(null=True, blank=True, verbose_name="Datum prodeje", db_column='Vystaveno')
    kod = models.CharField(max_length=100, null=True, blank=True, verbose_name="Kód položky", db_column='Kod')
    nazev = models.TextField(null=True, blank=True, verbose_name="Název položky", db_column='Nazev')
    
    # Doklad
    doklad = models.CharField(max_length=100, null=True, blank=True, verbose_name="Číslo účtenky/faktury", db_column='Doklad')
    objednavka = models.CharField(max_length=100, null=True, blank=True, verbose_name="Číslo objednávky", db_column='Objednavka')
    pokladna = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pokladna", db_column='Pokladna')
    
    # Místo prodeje a personál
    stredisko = models.CharField(max_length=100, null=True, blank=True, verbose_name="Název prodejny", db_column='Stredisko')
    spravce = models.CharField(max_length=100, null=True, blank=True, verbose_name="Správce", db_column='Spravce')
    
    # Poznámky
    poznamka = models.TextField(null=True, blank=True, verbose_name="Poznámka k položce", db_column='Poznamka')
    poznamka_zakaznika = models.TextField(null=True, blank=True, verbose_name="Poznámka zákazníka", db_column='Poznamka_zakaznika')
    objednavku_zalozil = models.CharField(max_length=100, null=True, blank=True, verbose_name="Objednávku založil", db_column='Objednavku_zalozil')
    
    # Množství a ceny
    pocet_kusu = models.IntegerField(null=True, blank=True, verbose_name="Počet kusů", db_column='Pocet_kusu')
    cena_ks_vcl_dph = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Prodejní cena s DPH", db_column='Cena_ks_vcl_DPH')
    cena_ks_bez_dph = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Prodejní cena bez DPH", db_column='Cena_ks_bez_DPH')
    skladova_cena_bez_dph = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Nákupní cena bez DPH", db_column='Skladova_cena_bez_DPH')
    
    # Kategorie původní a technik
    kategorie_puvodni = models.TextField(null=True, blank=True, verbose_name="Původní kategorie", db_column='Kategorie_puvodni')
    
    # Prodejní kanály
    marketingovy_kanal = models.CharField(max_length=100, null=True, blank=True, verbose_name="Marketing kanál", db_column='Marketingovy_kanal')
    dropshipping = models.CharField(max_length=10, null=True, blank=True, verbose_name="Dropshipping", db_column='Dropshipping')
    
    # Identifikátory
    id_prodejce = models.IntegerField(null=True, blank=True, verbose_name="ID prodejce", db_column='ID_PRODEJCE')
    id_prodejny = models.IntegerField(null=True, blank=True, verbose_name="ID prodejny", db_column='ID_PRODEJNY')
    
    # Zisk
    zisk = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Zisk", db_column='ZISK')
    
    # Kategorie produktů
    kategorie = models.CharField(max_length=255, null=True, blank=True, verbose_name="Hlavní kategorie", db_column='KATEGORIE')
    kategorie_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Podkategorie 1", db_column='KATEGORIE_1')
    kategorie_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Podkategorie 2", db_column='KATEGORIE_2')
    
    # Technik a servis
    technik = models.CharField(max_length=100, null=True, blank=True, verbose_name="Technik", db_column='Technik')
    k_servisu = models.CharField(max_length=10, null=True, blank=True, verbose_name="K servisu", db_column='k_servisu')
    
    # Metadata
    datum_vlozeni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vložení do DB", db_column='datum_vlozeni')
    cas_prodeje = models.TimeField(null=True, blank=True, verbose_name="Čas prodeje", db_column='cas_prodeje')
    
    class Meta:
        db_table = 'WEB_PRODEJE_ALL'
        verbose_name = 'Prodejní položka (ALL)'
        verbose_name_plural = 'Prodejní položky (ALL)'
        ordering = ['-datum_vlozeni', '-id']
    
    def __str__(self):
        return f"ALL: {self.typ} - {self.nazev} ({self.cena_ks_vcl_dph} Kč)"
    
    @property
    def celkova_cena(self):
        """Celková prodejní cena (počet kusů × cena za kus)"""
        if self.pocet_kusu and self.cena_ks_vcl_dph:
            return self.pocet_kusu * self.cena_ks_vcl_dph
        return self.cena_ks_vcl_dph or 0
    
    @property
    def celkovy_zisk(self):
        """Celkový zisk (počet kusů × zisk za kus)"""
        if self.pocet_kusu and self.zisk:
            return self.pocet_kusu * self.zisk
        return self.zisk or 0


class WebZasilkovna(models.Model):
    """
    Model pro tabulku WEB_ZASILKOVNA - provizní data ze Zásilkovny (Packeta)
    Obsahuje měsíční provizní data ze všech 6 prodejen
    """
    
    # Základní identifikace
    id = models.AutoField(primary_key=True, db_column='ID')
    prodejna = models.CharField(max_length=100, verbose_name="Název prodejny", db_column='PRODEJNA')
    id_prodejna = models.IntegerField(verbose_name="ID prodejny", db_column='ID_PRODEJNA')
    
    # Časové období
    rok = models.IntegerField(verbose_name="Rok", db_column='ROK')
    mesic = models.IntegerField(verbose_name="Měsíc", db_column='MESIC')
    
    # Provize
    za_zpracovani = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Za zpracování", db_column='ZA_ZPRACOVANI')
    za_vyber_dobirky = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Za výběr dobírky", db_column='ZA_VYBER_DOBIRKY')
    ostatni_provize = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Ostatní provize", db_column='OSTATNI_PROVIZE')
    celkove_provize_mesic = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Celkové provize za měsíc", db_column='CELKOVE_PROVIZE_MESIC')
    k_vyplate_mesic = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="K výplatě za měsíc", db_column='K_VYPLATE_MESIC')
    
    # Status
    fakturovano = models.CharField(max_length=10, default='NE', verbose_name="Fakturováno", db_column='FAKTUROVANO')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření", db_column='CREATED_AT')
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Datum aktualizace", db_column='UPDATED_AT')
    
    class Meta:
        db_table = 'WEB_ZASILKOVNA'
        verbose_name = 'Zásilkovna provize'
        verbose_name_plural = 'Zásilkovna provize'
        ordering = ['-rok', '-mesic', 'prodejna']
        unique_together = ['prodejna', 'rok', 'mesic']
        indexes = [
            models.Index(fields=['rok', 'mesic'], name='idx_zasilkovna_rok_mesic'),
            models.Index(fields=['id_prodejna'], name='idx_zasilkovna_prodejna'),
        ]
    
    def __str__(self):
        return f"{self.prodejna} - {self.rok}/{self.mesic:02d} - {self.celkove_provize_mesic} Kč"


class WebVykupy(models.Model):
    """
    Model pro tabulku WEB_VYKUPY - data o výkupech zboží z bazaru
    """
    id = models.AutoField(primary_key=True)
    vystaveno = models.DateField(db_column='Vystaveno')
    vystaveno_cas = models.TimeField(db_column='Vystaveno_cas', null=True, blank=True)
    kod = models.CharField(max_length=50, db_column='Kod', null=True, blank=True)
    nazev = models.TextField(db_column='Nazev', null=True, blank=True)
    stredisko = models.CharField(max_length=100, db_column='Stredisko', null=True, blank=True)
    pocet_kusů = models.IntegerField(db_column='Pocet_kusu', default=0)
    cena_ks_bez_dph = models.DecimalField(max_digits=12, decimal_places=2, db_column='Cena_ks_bez_DPH', null=True, blank=True)
    spravce = models.CharField(max_length=100, db_column='Spravce', null=True, blank=True)
    kategorie = models.CharField(max_length=100, db_column='Kategorie', null=True, blank=True)
    id_prodejny = models.IntegerField(db_column='ID_PRODEJNY', null=True, blank=True)
    id_prodejce = models.IntegerField(db_column='ID_PRODEJCE', null=True, blank=True)

    class Meta:
        db_table = 'WEB_VYKUPY'
        managed = False  # Tabulku spravuje externí actor
        verbose_name = 'Výkup'
        verbose_name_plural = 'Výkupy'

    def __str__(self):
        return f"{self.vystaveno} - {self.nazev} ({self.cena_ks_bez_dph} Kč)"
