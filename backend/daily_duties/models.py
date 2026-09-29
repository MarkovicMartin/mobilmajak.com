from django.core.exceptions import ValidationError
from django.db import models

from .periods import ACTIVE_PERIODS


class DailyDutyTemplate(models.Model):
    """Šablona povinnosti na prodejnu, nebo na jednoho uživatele."""

    PERIODICITY_CHOICES = [
        ('daily', 'Denně'),
        ('weekly', 'Týdně'),
        ('monthly', 'Měsíčně'),
    ]

    title = models.CharField(max_length=200, verbose_name='Název')
    description = models.TextField(blank=True, default='', verbose_name='Popis')
    periodicity = models.CharField(max_length=20, choices=PERIODICITY_CHOICES, default='daily')
    prodejna = models.ForeignKey(
        'stores.Prodejna',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='daily_duty_templates',
        verbose_name='Prodejna',
    )
    uzivatel = models.ForeignKey(
        'users.WebUser',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='daily_duty_templates',
        verbose_name='Uživatel',
    )
    # Stará textová pole ze scaffoldu. Nové šablony je nepoužívají.
    store = models.CharField(max_length=100, blank=True, default='', verbose_name='Prodejna (text)')
    role = models.CharField(max_length=50, blank=True, default='', verbose_name='Role (text)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_DENNI_POVINNOSTI'
        verbose_name = 'Denní povinnost'
        verbose_name_plural = 'Denní povinnosti'
        ordering = ['title']

    def __str__(self):
        return self.title

    def clean(self):
        if self.periodicity not in ACTIVE_PERIODS:
            raise ValidationError({'periodicity': 'Povolené hodnoty jsou denně, týdně a měsíčně.'})
        if bool(self.prodejna_id) == bool(self.uzivatel_id):
            raise ValidationError('Šablona musí mířit buď na prodejnu, nebo na jednoho uživatele.')


class DailyDutyCompletion(models.Model):
    """Jedno splnění šablony za období (den, ISO týden, nebo kalendářní měsíc)."""

    template = models.ForeignKey(
        DailyDutyTemplate,
        on_delete=models.CASCADE,
        related_name='completions',
    )
    period_start = models.DateField(verbose_name='Začátek období')
    completed_by = models.ForeignKey(
        'users.WebUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='daily_duty_completions',
    )
    note = models.TextField(blank=True, default='', verbose_name='Poznámka')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'WEB_DENNI_POVINNOSTI_SPLNENI'
        verbose_name = 'Splnění povinnosti'
        verbose_name_plural = 'Splnění povinností'
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'period_start'],
                name='daily_duty_one_completion_per_period',
            ),
        ]
        ordering = ['-period_start']

    def __str__(self):
        return f'{self.template_id} @ {self.period_start}'
