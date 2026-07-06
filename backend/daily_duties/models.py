from django.db import models


class DailyDutyTemplate(models.Model):
    """Šablona denní/týdenní povinnosti – testovací modul."""

    PERIODICITY_CHOICES = [
        ('daily', 'Denně'),
        ('shift', 'Po směně'),
        ('weekly', 'Týdně'),
    ]

    title = models.CharField(max_length=200, verbose_name='Název')
    description = models.TextField(blank=True, default='', verbose_name='Popis')
    periodicity = models.CharField(max_length=20, choices=PERIODICITY_CHOICES, default='daily')
    store = models.CharField(max_length=100, blank=True, default='', verbose_name='Prodejna')
    role = models.CharField(max_length=50, blank=True, default='', verbose_name='Role')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_DENNI_POVINNOSTI'
        verbose_name = 'Denní povinnost'
        verbose_name_plural = 'Denní povinnosti'
        ordering = ['store', 'title']

    def __str__(self):
        return self.title
