from django.db import models
from users.models import WebUser
from stores.models import Prodejna


LOCK_MODE_CHOICES = [
    ('none', 'Auto (dopočet)'),
    ('pct',  'Zamčené procento'),
    ('kc',   'Zamčená absolutní částka'),
]


class PlanMonth(models.Model):
    """Měsíční plán firmy – jedna verze plánu pro daný měsíc"""

    rok = models.IntegerField(verbose_name="Rok")
    mesic = models.IntegerField(verbose_name="Měsíc (1–12)")
    cislo_verze = models.IntegerField(default=1, verbose_name="Číslo verze")
    je_aktualni = models.BooleanField(default=True, verbose_name="Je aktuální verze")
    castka_celkem = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Celková částka firmy (Kč)"
    )
    total_lock = models.BooleanField(
        default=False, verbose_name="Celková částka pevná"
    )
    vytvoreno_kdy = models.DateTimeField(auto_now_add=True, verbose_name="Vytvořeno kdy")
    vytvoril = models.ForeignKey(
        WebUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='plany_vytvorene', verbose_name="Vytvořil"
    )

    class Meta:
        db_table = 'WEB_PLANS_MONTH'
        verbose_name = "Měsíční plán"
        verbose_name_plural = "Měsíční plány"
        unique_together = [('rok', 'mesic', 'cislo_verze')]
        ordering = ['-rok', '-mesic', '-cislo_verze']

    def __str__(self):
        return f"{self.mesic}/{self.rok} v{self.cislo_verze}"

    def save(self, *args, **kwargs):
        if self.je_aktualni:
            PlanMonth.objects.filter(
                rok=self.rok, mesic=self.mesic, je_aktualni=True
            ).exclude(pk=self.pk).update(je_aktualni=False)
        super().save(*args, **kwargs)


class PlanStore(models.Model):
    """Rozpad měsíčního plánu na prodejny"""

    plan_mesic = models.ForeignKey(
        PlanMonth, on_delete=models.CASCADE, related_name='prodejny',
        verbose_name="Měsíční plán"
    )
    prodejna = models.ForeignKey(
        Prodejna, on_delete=models.CASCADE, related_name='plany',
        verbose_name="Prodejna"
    )
    podil_procenta = models.DecimalField(
        max_digits=6, decimal_places=3, verbose_name="Podíl (%)"
    )
    castka_prodejna = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Částka prodejny (Kč)"
    )
    zamknuto = models.BooleanField(default=False, verbose_name="Zamknuto (legacy)")
    lock_mode = models.CharField(
        max_length=8, choices=LOCK_MODE_CHOICES, default='none',
        verbose_name="Režim zámku prodejny"
    )
    servis_lock_mode = models.CharField(
        max_length=8, choices=LOCK_MODE_CHOICES, default='none',
        verbose_name="Režim zámku prodej/servis"
    )
    castka_prodej = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Částka prodej (Kč)"
    )
    castka_servis = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Částka servis (Kč)"
    )

    class Meta:
        db_table = 'WEB_PLANS_STORE'
        verbose_name = "Plán prodejny"
        verbose_name_plural = "Plány prodejen"
        unique_together = [('plan_mesic', 'prodejna')]
        ordering = ['prodejna__poradi', 'prodejna__nazev']

    def __str__(self):
        return f"{self.plan_mesic} – {self.prodejna.nazev}"


KATEGORIE_CHOICES = [
    ('NOVE_TELEFONY', 'Telefony nové'),
    ('BAZAROVE_TELEFONY', 'Telefony bazarové'),
    ('PRISLUSENSTVI', 'Příslušenství'),
    ('PRISLUSENSTVI_SKLA', 'Příslušenství – Skla'),
    ('PRISLUSENSTVI_OBALY', 'Příslušenství – Obaly'),
    ('PRISLUSENSTVI_OSTATNI', 'Příslušenství – Ostatní'),
    ('SLUZBY', 'Služby'),
    ('SERVIS', 'Servis'),
    ('OSTATNI', 'Ostatní'),
]


class PlanCategory(models.Model):
    """Rozpad plánu prodejny na kategorie"""

    plan_prodejna = models.ForeignKey(
        PlanStore, on_delete=models.CASCADE, related_name='kategorie',
        verbose_name="Plán prodejny"
    )
    kategorie_kod = models.CharField(
        max_length=30, choices=KATEGORIE_CHOICES, verbose_name="Kategorie"
    )
    podil_procenta = models.DecimalField(
        max_digits=6, decimal_places=3, verbose_name="Podíl v rámci prodejny (%)"
    )
    castka_kategorie = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Částka kategorie (Kč)"
    )
    prumerna_cena_za_kus = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Průměrná cena za kus (Kč)"
    )
    lock_mode = models.CharField(
        max_length=8, choices=LOCK_MODE_CHOICES, default='none',
        verbose_name="Režim zámku kategorie"
    )

    class Meta:
        db_table = 'WEB_PLANS_CATEGORY'
        verbose_name = "Plán kategorie"
        verbose_name_plural = "Plány kategorií"
        unique_together = [('plan_prodejna', 'kategorie_kod')]
        ordering = ['kategorie_kod']

    def __str__(self):
        return f"{self.plan_prodejna} – {self.get_kategorie_kod_display()}"


class PlanProdejce(models.Model):
    """Plán konkrétního prodejce na konkrétní prodejně pro daný měsíc"""

    plan_prodejna = models.ForeignKey(
        PlanStore, on_delete=models.CASCADE, related_name='plany_prodejcu',
        verbose_name="Plán prodejny"
    )
    uzivatel = models.ForeignKey(
        WebUser, on_delete=models.CASCADE, related_name='plany_prodejce',
        verbose_name="Prodejce"
    )

    class Meta:
        db_table = 'WEB_PLANS_PRODEJCE'
        verbose_name = "Plán prodejce"
        verbose_name_plural = "Plány prodejců"
        unique_together = [('plan_prodejna', 'uzivatel')]
        ordering = ['uzivatel__jmeno', 'uzivatel__prijmeni']

    def __str__(self):
        return f"{self.plan_prodejna} – {self.uzivatel.jmeno} {self.uzivatel.prijmeni}"


class PlanProdejceKategorie(models.Model):
    """Plánované kusy/obrat prodejce per kategorie"""

    plan_prodejce = models.ForeignKey(
        PlanProdejce, on_delete=models.CASCADE, related_name='kategorie',
        verbose_name="Plán prodejce"
    )
    kategorie_kod = models.CharField(
        max_length=30, choices=KATEGORIE_CHOICES, verbose_name="Kategorie"
    )
    pocet_kusu = models.IntegerField(default=0, verbose_name="Plánované kusy")
    castka = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Plánovaná částka (Kč)"
    )
    lock_mode = models.CharField(
        max_length=8, choices=LOCK_MODE_CHOICES, default='none',
        verbose_name="Režim zámku (prodejce × kategorie)"
    )

    class Meta:
        db_table = 'WEB_PLANS_PRODEJCE_KAT'
        verbose_name = "Plán prodejce – kategorie"
        verbose_name_plural = "Plány prodejců – kategorie"
        unique_together = [('plan_prodejce', 'kategorie_kod')]
        ordering = ['kategorie_kod']

    def __str__(self):
        return f"{self.plan_prodejce} – {self.kategorie_kod}"
