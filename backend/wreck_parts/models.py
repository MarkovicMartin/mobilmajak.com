from django.db import models


class WreckPart(models.Model):
    """Díl z vraku – sdílený seznam per prodejna."""

    model_name = models.CharField(max_length=200, verbose_name='Model')
    part_type = models.CharField(max_length=100, verbose_name='Typ dílu')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Počet')
    store = models.CharField(max_length=100, verbose_name='Prodejna')
    notes = models.TextField(blank=True, default='', verbose_name='Poznámka')
    is_active = models.BooleanField(default=True, verbose_name='Aktivní')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_DILY_Z_VRAKU'
        verbose_name = 'Díl z vraku'
        verbose_name_plural = 'Díly z vraků'
        ordering = ['store', 'model_name', 'part_type']

    def __str__(self):
        return f'{self.model_name} – {self.part_type} ({self.store})'
