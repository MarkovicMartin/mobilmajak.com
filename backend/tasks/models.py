from django.db import models


class Ukol(models.Model):
    """Model pro jednoduché úkoly přiřazené prodejci (WEB_UKOLY)."""

    STAVY = [
        ("novy", "Nový"),
        ("v_procesu", "V procesu"),
        ("hotovo", "Hotovo"),
    ]

    PRIORITY = [
        ("nizka", "Nízká"),
        ("stredni", "Střední"),
        ("vysoka", "Vysoká"),
    ]

    TYPY = [
        ("prirazeny", "Přiřazený"),
        ("osobni", "Osobní"),
    ]

    id = models.AutoField(primary_key=True)
    ukol = models.CharField(max_length=255, db_column="UKOL")
    priorita = models.CharField(
        max_length=50,
        choices=PRIORITY,
        default="stredni",
        db_column="PRIORITA",
    )
    deadline = models.DateField(null=True, blank=True, db_column="DEADLINE")
    deadline_cas = models.TimeField(null=True, blank=True, db_column="DEADLINE_CAS")
    stav = models.CharField(max_length=20, choices=STAVY, default="novy", db_column="STAV")
    typ = models.CharField(max_length=20, choices=TYPY, default="osobni", db_column="TYP")
    precteno_v = models.DateTimeField(null=True, blank=True, db_column="PRECTENO_V")
    id_prodejce_ukol = models.IntegerField(db_column="ID_PRODEJCE_UKOL")
    id_prodejce_zadal = models.IntegerField(db_column="ID_PRODEJCE_ZADAL")
    id_prodejny = models.IntegerField(null=True, blank=True, db_column="ID_PRODEJNY")
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column="VYTVORENO")
    upraveno = models.DateTimeField(auto_now=True, db_column="UPRAVENO")

    class Meta:
        db_table = "WEB_UKOLY"
        ordering = ["-vytvoreno"]
        indexes = [
            models.Index(fields=["id_prodejce_ukol"], name="idx_ukoly_prodejce"),
            models.Index(fields=["stav"], name="idx_ukoly_stav"),
            models.Index(fields=["id_prodejny"], name="idx_ukoly_prodejna"),
            models.Index(fields=["typ"], name="idx_ukoly_typ"),
        ]

    def __str__(self) -> str:
        return f"Ukol #{self.id}: {self.ukol}"


class UkolKomentar(models.Model):
    id = models.AutoField(primary_key=True)
    ukol = models.ForeignKey(
        Ukol,
        related_name="komentare",
        on_delete=models.CASCADE,
        db_column="UKOL_ID",
    )
    autor_id = models.IntegerField(db_column="AUTOR_ID")
    autor_jmeno = models.CharField(max_length=100, db_column="AUTOR_JMENO", blank=True, default="")
    text = models.TextField(db_column="TEXT")
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column="VYTVORENO")

    class Meta:
        db_table = "WEB_UKOLY_KOMENTARE"
        ordering = ["vytvoreno"]

    def __str__(self) -> str:
        return f"Komentář k úkolu #{self.ukol_id}"
