from django.db import models


class Ukol(models.Model):
    """Model pro jednoduché úkoly přiřazené prodejci (WEB_UKOLY)."""

    STAVY = [
        ("novy", "Nový"),
        ("v_procesu", "V procesu"),
        ("hotovo", "Hotovo"),
    ]

    id = models.AutoField(primary_key=True)
    ukol = models.CharField(max_length=255, db_column="UKOL")
    priorita = models.CharField(max_length=50, db_column="PRIORITA")
    deadline = models.DateField(null=True, blank=True, db_column="DEADLINE")
    stav = models.CharField(max_length=20, choices=STAVY, default="novy", db_column="STAV")
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
        ]

    def __str__(self) -> str:
        return f"Ukol #{self.id}: {self.ukol}"


