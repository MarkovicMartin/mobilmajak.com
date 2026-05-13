from django.db import models
from users.models import WebUser
import os
import uuid

def get_file_path(instance, filename):
    """Generuje unikátní cestu pro soubory"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('news_files', filename)

class Kategorie(models.Model):
    """Model pro kategorie příspěvků"""
    id = models.AutoField(primary_key=True)
    nazev = models.CharField(max_length=100, unique=True, verbose_name="Název kategorie")
    barva = models.CharField(max_length=7, default="#0066cc", verbose_name="Barva kategorie (hex)")
    ikona = models.CharField(max_length=50, blank=True, verbose_name="CSS ikona")
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní")
    
    class Meta:
        db_table = 'WEB_NOVINKY_KATEGORIE'
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorie"
        ordering = ['nazev']
    
    def __str__(self):
        return self.nazev

class NovinkaKategorie(models.Model):
    """Intermediate model pro M2M vztah mezi Novinka a Kategorie"""
    id = models.AutoField(primary_key=True)
    novinka = models.ForeignKey('Novinka', on_delete=models.CASCADE)
    kategorie = models.ForeignKey(Kategorie, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'WEB_NOVINKY_KATEGORIE_M2M'
        unique_together = [['novinka', 'kategorie']]

class Novinka(models.Model):
    """Model pro novinkové příspěvky"""
    id = models.AutoField(primary_key=True)
    autor = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='novinky')
    obsah = models.TextField(verbose_name="Obsah příspěvku")
    kategorie = models.ManyToManyField(Kategorie, through=NovinkaKategorie, blank=True, related_name='novinky', verbose_name="Kategorie")
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_upravy = models.DateTimeField(auto_now=True, verbose_name="Datum úpravy")
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní")
    
    class Meta:
        db_table = 'WEB_NOVINKY'
        verbose_name = "Novinka"
        verbose_name_plural = "Novinky"
        ordering = ['-datum_vytvoreni']
    
    def __str__(self):
        return f"Novinka {self.id} od {self.autor.jmeno} {self.autor.prijmeni}"
    
    @property
    def pocet_reakci(self):
        """Vrátí celkový počet reakcí na příspěvek"""
        return self.reakce.count()
    
    @property
    def pocet_komentaru(self):
        """Vrátí počet komentářů na příspěvek"""
        return self.komentare.count()

class NovinkaSoubor(models.Model):
    """Model pro soubory připojené k novinkám"""
    TYP_CHOICES = [
        ('obrazek', 'Obrázek'),
        ('dokument', 'Dokument'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('jiny', 'Jiný'),
    ]
    
    id = models.AutoField(primary_key=True)
    novinka = models.ForeignKey(Novinka, on_delete=models.CASCADE, related_name='soubory')
    soubor = models.FileField(upload_to=get_file_path, verbose_name="Soubor")
    nazev = models.CharField(max_length=255, verbose_name="Název souboru")
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='jiny', verbose_name="Typ souboru")
    velikost = models.IntegerField(verbose_name="Velikost v bytech")
    datum_nahrani = models.DateTimeField(auto_now_add=True, verbose_name="Datum nahrání")
    
    class Meta:
        db_table = 'WEB_NOVINKY_SOUBORY'
        verbose_name = "Soubor novinky"
        verbose_name_plural = "Soubory novinek"
    
    def __str__(self):
        return f"{self.nazev} ({self.novinka.id})"
    
    def save(self, *args, **kwargs):
        if not self.velikost and self.soubor:
            self.velikost = self.soubor.size
        super().save(*args, **kwargs)

class Reakce(models.Model):
    """Model pro reakce na novinky (like, dislike, emoji)"""
    TYP_CHOICES = [
        ('like', '👍 Like'),
        ('dislike', '👎 Dislike'),
        ('srdce', '❤️ Srdce'),
        ('smich', '😂 Smích'),
        ('smutek', '😢 Smutek'),
        ('hnev', '😠 Hněv'),
        ('prekvapeni', '😮 Překvapení'),
    ]
    
    id = models.AutoField(primary_key=True)
    novinka = models.ForeignKey(Novinka, on_delete=models.CASCADE, related_name='reakce')
    uzivatel = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='reakce')
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='like', verbose_name="Typ reakce")
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    
    class Meta:
        db_table = 'WEB_NOVINKY_REAKCE'
        verbose_name = "Reakce"
        verbose_name_plural = "Reakce"
        unique_together = ['novinka', 'uzivatel']  # Jeden uživatel může mít jen jednu reakci na příspěvek
    
    def __str__(self):
        return f"{self.uzivatel.jmeno} {self.typ} na novinku {self.novinka.id}"

class Komentar(models.Model):
    """Model pro komentáře k novinkám"""
    id = models.AutoField(primary_key=True)
    novinka = models.ForeignKey(Novinka, on_delete=models.CASCADE, related_name='komentare')
    autor = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='komentare')
    obsah = models.TextField(verbose_name="Obsah komentáře")
    datum_vytvoreni = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    datum_upravy = models.DateTimeField(auto_now=True, verbose_name="Datum úpravy")
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní")
    
    class Meta:
        db_table = 'WEB_NOVINKY_KOMENTARE'
        verbose_name = "Komentář"
        verbose_name_plural = "Komentáře"
        ordering = ['datum_vytvoreni']
    
    def __str__(self):
        return f"Komentář {self.id} od {self.autor.jmeno} na novinku {self.novinka.id}"

class KomentarSoubor(models.Model):
    """Model pro soubory připojené k komentářům"""
    TYP_CHOICES = [
        ('obrazek', 'Obrázek'),
        ('dokument', 'Dokument'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('jiny', 'Jiný'),
    ]
    
    id = models.AutoField(primary_key=True)
    komentar = models.ForeignKey(Komentar, on_delete=models.CASCADE, related_name='soubory')
    soubor = models.FileField(upload_to=get_file_path, verbose_name="Soubor")
    nazev = models.CharField(max_length=255, verbose_name="Název souboru")
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='jiny', verbose_name="Typ souboru")
    velikost = models.IntegerField(verbose_name="Velikost v bytech")
    datum_nahrani = models.DateTimeField(auto_now_add=True, verbose_name="Datum nahrání")
    
    class Meta:
        db_table = 'WEB_NOVINKY_KOMENTARE_SOUBORY'
        verbose_name = "Soubor komentáře"
        verbose_name_plural = "Soubory komentářů"
    
    def __str__(self):
        return f"{self.nazev} (komentář {self.komentar.id})"
    
    def save(self, *args, **kwargs):
        if not self.velikost and self.soubor:
            self.velikost = self.soubor.size
        super().save(*args, **kwargs)
