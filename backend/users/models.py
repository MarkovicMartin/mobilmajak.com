from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class WebUser(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrátor'),
        ('VEDOUCI', 'Vedoucí'),
        ('PRODEJCE', 'Prodejce'),
    ]
    
    # Primární klíč - ručně zadaný ID
    id = models.IntegerField(primary_key=True)
    
    # Základní informace
    uzivatelske_jmeno = models.CharField(max_length=50, unique=True, verbose_name="Uživatelské jméno", default="temp")
    jmeno = models.CharField(max_length=50, verbose_name="Jméno")
    prijmeni = models.CharField(max_length=50, verbose_name="Příjmení", default="")
    heslo = models.CharField(max_length=255, verbose_name="Heslo")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PRODEJCE', verbose_name="Role")
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní")
    
    # Nové osobní údaje
    # prodejna = models.ForeignKey('stores.Prodejna', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Prodejna", related_name='uzivatele')
    prodejna_id = models.IntegerField(null=True, blank=True, verbose_name="ID domovské prodejny")
    technik_id = models.IntegerField(null=True, blank=True, verbose_name="ID technika (EDA/Pohoda)")
    telefon = models.CharField(max_length=20, verbose_name="Telefonní číslo", blank=True, null=True)
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    adresa = models.TextField(verbose_name="Adresa", blank=True, null=True)
    poznamka = models.TextField(verbose_name="Poznámka", blank=True, null=True)
    
    # Moduly - JSON pole pro uložení povolených modulů
    moduly = models.JSONField(default=list, verbose_name="Povolené moduly")

    # Mzdové údaje (body) – viditelné jen pro ADMIN v administraci a exportu
    mzda_zaklad = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Měsíční základ (body)",
    )
    mzda_doplnky = models.JSONField(
        default=list, blank=True,
        verbose_name="Volitelné mzdové doplňky (body)",
    )
    
    # Časové údaje
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Poslední přihlášení")
    
    class Meta:
        db_table = 'WEB_USERS'
        verbose_name = "Uživatel"
        verbose_name_plural = "Uživatelé"
    
    def __str__(self):
        return f"{self.id} - {self.uzivatelske_jmeno} ({self.jmeno} {self.prijmeni})"
    
    def set_heslo(self, raw_heslo):
        """Bezpečně nastaví heslo pomocí hashování"""
        self.heslo = make_password(raw_heslo)
    
    def check_heslo(self, raw_heslo):
        """Ověří heslo"""
        # 1) Standardní Django ověření hashovaného hesla
        if check_password(raw_heslo, self.heslo):
            return True

        # 2) Fallback: legacy plaintext hesla (auto-upgrade na hash)
        # Pokud uložené heslo nevypadá jako Django hash, ověříme přímo a při úspěchu jej přeuložíme jako hash
        legacy_like = ('$' not in self.heslo) and not (
            self.heslo.startswith('pbkdf2_') or
            self.heslo.startswith('argon2') or
            self.heslo.startswith('bcrypt') or
            self.heslo.startswith('sha1$')
        )

        if legacy_like and self.heslo == raw_heslo:
            # Automatické přeuložení na bezpečný hash
            self.set_heslo(raw_heslo)
            # Uložíme pouze pole heslo kvůli výkonu a bezpečnosti
            self.save(update_fields=['heslo'])
            return True

        return False
    
    def ma_pristup_k_modulu(self, modul):
        """Zkontroluje, zda má uživatel přístup k danému modulu"""
        return modul in self.moduly
    
    def pridej_modul(self, modul):
        """Přidá modul do seznamu povolených modulů"""
        if modul not in self.moduly:
            self.moduly.append(modul)
    
    def odeber_modul(self, modul):
        """Odebere modul ze seznamu povolených modulů"""
        if modul in self.moduly:
            self.moduly.remove(modul)
    
    # Django REST Framework požadované atributy
    @property
    def is_authenticated(self):
        """Vrátí True, pokud je uživatel přihlášen"""
        return True
    
    @property
    def is_active(self):
        """Vrátí True, pokud je uživatel aktivní"""
        return self.aktivni
    
    @property
    def is_anonymous(self):
        """Vrátí False, protože toto není anonymní uživatel"""
        return False
    
    @property
    def backend(self):
        """Vrátí název autentifikačního backendu"""
        return 'users.auth_backend.WebUserAuthBackend'


class ProfilovyObrazek(models.Model):
    """Model pro ukládání profilových obrázků uživatelů"""
    
    uzivatel = models.OneToOneField(WebUser, on_delete=models.CASCADE, related_name='profilovy_obrazek', verbose_name="Uživatel")
    obrazek = models.ImageField(upload_to='profilove_obrazky/', verbose_name="Profilový obrázek")
    datum_nahrani = models.DateTimeField(auto_now_add=True, verbose_name="Datum nahrání")
    
    class Meta:
        db_table = 'WEB_PROFILOVE_OBRAZKY'
        verbose_name = "Profilový obrázek"
        verbose_name_plural = "Profilové obrázky"
    
    def __str__(self):
        return f"Profilový obrázek: {self.uzivatel.jmeno} {self.uzivatel.prijmeni}"
