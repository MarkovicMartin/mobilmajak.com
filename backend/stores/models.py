from django.db import models

# Create your models here.

class Prodejna(models.Model):
    """Model pro prodejny"""
    
    # ID bude auto-increment, ale můžeme upravit podle potřeby
    id = models.AutoField(primary_key=True)
    
    # Základní informace
    nazev = models.CharField(max_length=100, unique=True, verbose_name="Název prodejny")
    nazev_kratkiy = models.CharField(max_length=20, verbose_name="Krátký název", help_text="Pro zobrazení v tabulkách")
    nazev_google_sheets = models.CharField(max_length=100, blank=True, null=True, verbose_name="Název v Google Sheets", help_text="Jak se prodejna jmenuje v Google tabulce")
    
    # Kontaktní informace
    adresa = models.TextField(blank=True, null=True, verbose_name="Adresa")
    telefon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")
    
    # Provozní informace
    otevreno_od = models.TimeField(blank=True, null=True, verbose_name="Otevřeno od")
    otevreno_do = models.TimeField(blank=True, null=True, verbose_name="Otevřeno do")
    vedouci_prodejny = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vedoucí prodejny")
    
    # Nastavení
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní")
    barva = models.CharField(max_length=7, default="#0066cc", verbose_name="Barva (hex kód)", help_text="Pro rozlišení v grafech a UI")
    poradi = models.IntegerField(default=0, verbose_name="Pořadí", help_text="Pro řazení v seznamech")
    
    # Poznámky
    poznamka = models.TextField(blank=True, null=True, verbose_name="Poznámka")
    
    # Časové údaje
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_upravy = models.DateTimeField(auto_now=True, verbose_name="Datum úpravy")
    
    class Meta:
        db_table = 'WEB_PRODEJNY'
        verbose_name = "Prodejna"
        verbose_name_plural = "Prodejny"
        ordering = ['poradi', 'nazev']
    
    def __str__(self):
        return self.nazev
    
    @property
    def je_aktivni(self):
        """Zkontroluje, zda je prodejna aktivní"""
        return self.aktivni
    
    @classmethod
    def get_aktivni_prodejny(cls):
        """Vrátí všechny aktivní prodejny"""
        return cls.objects.filter(aktivni=True).order_by('poradi', 'nazev')
    
    @classmethod
    def get_choices(cls):
        """Vrátí prodejny jako choices pro Django forms"""
        return [(p.id, p.nazev) for p in cls.get_aktivni_prodejny()]
