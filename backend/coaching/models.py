from django.db import models
from users.models import WebUser


class CoachingNote(models.Model):
    TYPY = [
        ('poznamka', 'Poznámka'),
        ('jedna_na_jednoho', '1:1'),
        ('zpetna_vazba', 'Zpětná vazba'),
    ]

    prodejce = models.ForeignKey(
        WebUser,
        on_delete=models.CASCADE,
        related_name='coaching_poznamky',
        db_column='PRODEJCE_ID',
    )
    autor = models.ForeignKey(
        WebUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='coaching_poznamky_autor',
        db_column='AUTOR_ID',
    )
    prodejna_id = models.IntegerField(null=True, blank=True, db_column='PRODEJNA_ID')
    typ = models.CharField(max_length=30, choices=TYPY, default='poznamka', db_column='TYP')
    text = models.TextField(db_column='TEXT')
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')
    upraveno = models.DateTimeField(auto_now=True, db_column='UPRAVENO')

    class Meta:
        db_table = 'WEB_COACHING_NOTES'
        ordering = ['-vytvoreno']


class CoachingGoal(models.Model):
    STAVY = [
        ('otevreny', 'Otevřený'),
        ('splneny', 'Splněný'),
        ('zruseny', 'Zrušený'),
    ]

    prodejce = models.ForeignKey(
        WebUser,
        on_delete=models.CASCADE,
        related_name='coaching_cile',
        db_column='PRODEJCE_ID',
    )
    autor = models.ForeignKey(
        WebUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='coaching_cile_autor',
        db_column='AUTOR_ID',
    )
    prodejna_id = models.IntegerField(null=True, blank=True, db_column='PRODEJNA_ID')
    nazev = models.CharField(max_length=255, db_column='NAZEV')
    popis = models.TextField(blank=True, default='', db_column='POPIS')
    kategorie_metrika = models.CharField(
        max_length=60, blank=True, default='', db_column='KATEGORIE_METRIKA',
    )
    cil_hodnota = models.CharField(max_length=64, blank=True, default='', db_column='CIL_HODNOTA')
    jednotka = models.CharField(max_length=32, blank=True, default='', db_column='JEDNOTKA')
    termin = models.DateField(null=True, blank=True, db_column='TERMIN')
    stav = models.CharField(max_length=20, choices=STAVY, default='otevreny', db_column='STAV')
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')
    dokonceno_v = models.DateTimeField(null=True, blank=True, db_column='DOKONCENO_V')

    class Meta:
        db_table = 'WEB_COACHING_GOALS'
        ordering = ['-vytvoreno']
