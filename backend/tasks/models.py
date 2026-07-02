from django.db import models


class Ukol(models.Model):
    """Model pro jednoduché úkoly přiřazené prodejci (WEB_UKOLY)."""

    STAVY = [
        ("novy", "Nový"),
        ("v_procesu", "V procesu"),
        ("blokovany", "Blokovaný"),
        ("ceka_schvaleni", "Čeká schválení"),
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

    ACTIVE_STAVY = ("novy", "v_procesu", "blokovany")

    id = models.AutoField(primary_key=True)
    ukol = models.CharField(max_length=255, db_column="UKOL")
    vysledek = models.TextField(blank=True, default="", db_column="VYSLEDEK")
    popis = models.TextField(blank=True, default="", db_column="POPIS")
    dod_polozky = models.JSONField(default=list, blank=True, db_column="DOD_POLOZKY")
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
    blokovano_duvod = models.TextField(blank=True, default="", db_column="BLOKOVANO_DUVOD")
    vyzaduje_schvaleni = models.BooleanField(default=False, db_column="VYZADUJE_SCHVALENI")
    schvaleno_v = models.DateTimeField(null=True, blank=True, db_column="SCHVALENO_V")
    schvalil_id = models.IntegerField(null=True, blank=True, db_column="SCHVALIL_ID")
    start_potvrzeno_v = models.DateTimeField(null=True, blank=True, db_column="START_POTVRZENO_V")
    prvni_krok = models.CharField(max_length=500, blank=True, default="", db_column="PRVNI_KROK")
    mid_kontrola_v = models.DateTimeField(null=True, blank=True, db_column="MID_KONTROLA_V")
    posledni_aktivita_v = models.DateTimeField(null=True, blank=True, db_column="POSLEDNI_AKTIVITA_V")
    precteno_v = models.DateTimeField(null=True, blank=True, db_column="PRECTENO_V")
    id_prodejce_ukol = models.IntegerField(db_column="ID_PRODEJCE_UKOL")
    id_prodejce_zadal = models.IntegerField(db_column="ID_PRODEJCE_ZADAL")
    id_prodejny = models.IntegerField(null=True, blank=True, db_column="ID_PRODEJNY")
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column="VYTVORENO")
    upraveno = models.DateTimeField(auto_now=True, db_column="UPRAVENO")
    dokonceno_v = models.DateTimeField(null=True, blank=True, db_column="DOKONCENO_V")

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
        title = (self.vysledek or self.ukol or "").strip()
        if title:
            return f"Ukol #{self.id}: {title[:80]}"
        return f"Ukol #{self.id}"


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


class UkolSlackNotifikace(models.Model):
    """Záznam odeslané Slack notifikace (zabraňuje duplicitám)."""

    TYPY = [
        ("due_soon", "Blíží se termín (webhook)"),
        ("overdue", "Po termínu (webhook)"),
        ("dm_assigned", "DM – přiřazení"),
        ("dm_due_soon", "DM – blíží se termín"),
        ("dm_overdue", "DM – po termínu"),
        ("dm_completed", "DM – hotovo"),
        ("dm_awaiting_approval", "DM – čeká schválení"),
        ("dm_created", "DM – potvrzení zadavateli"),
        ("dm_comment", "DM – nový komentář"),
    ]

    id = models.AutoField(primary_key=True)
    ukol = models.ForeignKey(
        Ukol,
        related_name="slack_notifikace",
        on_delete=models.CASCADE,
        db_column="UKOL_ID",
    )
    typ = models.CharField(max_length=30, choices=TYPY, db_column="TYP")
    recipient_user_id = models.IntegerField(
        null=True,
        blank=True,
        db_column="RECIPIENT_USER_ID",
        help_text="WebUser ID příjemce DM; null u webhook notifikací.",
    )
    odeslano_v = models.DateTimeField(auto_now_add=True, db_column="ODESLANO_V")
    ref_id = models.IntegerField(
        default=0,
        db_column="REF_ID",
        help_text="ID komentáře u dm_comment; u ostatních typů 0.",
    )

    class Meta:
        db_table = "WEB_UKOLY_SLACK_NOTIF"
        constraints = [
            models.UniqueConstraint(
                fields=["ukol", "typ", "recipient_user_id", "ref_id"],
                name="uniq_ukol_slack_typ_recipient_ref",
            ),
        ]

    def __str__(self) -> str:
        who = f" → user #{self.recipient_user_id}" if self.recipient_user_id else ""
        return f"Slack {self.typ}{who} pro úkol #{self.ukol_id}"


class SlackTaskDraft(models.Model):
    """Rozpracovaný úkol zakládaný přes Slack bota (wizard)."""

    slack_user_id = models.CharField(max_length=32, unique=True, db_column="SLACK_USER_ID")
    channel_id = models.CharField(max_length=32, blank=True, default="", db_column="CHANNEL_ID")
    web_user_id = models.IntegerField(db_column="WEB_USER_ID")
    step = models.CharField(max_length=40, db_column="STEP")
    data = models.JSONField(default=dict, blank=True, db_column="DATA")
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column="VYTVORENO")
    upraveno = models.DateTimeField(auto_now=True, db_column="UPRAVENO")

    class Meta:
        db_table = "WEB_UKOLY_SLACK_DRAFT"
        verbose_name = "Slack draft úkolu"
        verbose_name_plural = "Slack drafty úkolů"

    def __str__(self) -> str:
        return f"Slack draft {self.slack_user_id} krok={self.step}"


class UkolShiftRecapNotifikace(models.Model):
    """Odeslaný ranní recap úkolů ke směně (jednou za směnu)."""

    id = models.AutoField(primary_key=True)
    smena_id = models.IntegerField(unique=True, db_column="SMENA_ID")
    user_id = models.IntegerField(db_column="USER_ID")
    datum = models.DateField(db_column="DATUM")
    odeslano_v = models.DateTimeField(auto_now_add=True, db_column="ODESLANO_V")

    class Meta:
        db_table = "WEB_UKOLY_SHIFT_RECAP"
        indexes = [
            models.Index(fields=["datum"], name="idx_ukoly_recap_datum"),
        ]

    def __str__(self) -> str:
        return f"Shift recap směna #{self.smena_id} → user #{self.user_id}"
