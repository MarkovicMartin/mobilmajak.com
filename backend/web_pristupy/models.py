from django.db import models
from django.utils import timezone
from users.models import WebUser

class WEB_PRISTUPY_PRODEJNY(models.Model):
    """Model pro uložení přístupů k různým webovým službám podle prodejen"""
    
    id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=200, verbose_name="Název společnosti")
    website_url = models.URLField(max_length=500, verbose_name="URL adresa")
    username = models.CharField(max_length=100, verbose_name="Uživatelské jméno")
    password = models.CharField(max_length=255, verbose_name="Heslo")
    category = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Kategorie",
        help_text="Kategorie přístupu (např. Dodavatel, E-shop, Admin, atd.)"
    )
    store = models.CharField(max_length=100, verbose_name="Prodejna")
    description = models.TextField(blank=True, null=True, verbose_name="Popis")
    notes = models.TextField(blank=True, null=True, verbose_name="Poznámky")
    added_by = models.CharField(max_length=100, verbose_name="Přidal uživatel")
    last_used = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Poslední použití"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktivní")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vytvořeno")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualizováno")
    
    class Meta:
        db_table = 'WEB_PRISTUPY_PRODEJNY'
        verbose_name = "Přístup prodejny"
        verbose_name_plural = "Přístupy prodejen"
        ordering = ['store', 'company_name']
    
    def __str__(self):
        return f"{self.company_name} ({self.store})"
    
    def mark_as_used(self):
        """Označí přístup jako právě použitý"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
        
    @property
    def masked_password(self):
        """Vrátí zamaskované heslo pro bezpečné zobrazení"""
        if not self.password:
            return ""
        return "*" * min(len(self.password), 8)
    
    @classmethod
    def get_by_store(cls, store_name):
        """Vrátí všechny aktivní přístupy pro danou prodejnu"""
        return cls.objects.filter(store=store_name, is_active=True)
    
    @classmethod
    def get_all_stores(cls):
        """Vrátí seznam všech prodejen s počtem přístupů"""
        return (cls.objects
                .filter(is_active=True)
                .values('store')
                .annotate(count=models.Count('id'))
                .order_by('store'))
