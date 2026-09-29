import os
import uuid

from django.db import models


def knowledge_upload_path(instance, filename):
    """UUID cesta pod MEDIA, stejně jako soubory novinek."""
    ext = ''
    if filename and '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower()
    return os.path.join('knowledge', f'{uuid.uuid4()}{ext}')


class KnowledgeDocument(models.Model):
    """Soubor ve znalostní bázi. Text z PDF, DOCX a TXT je v extracted_text."""

    nazev = models.CharField(max_length=255, verbose_name='Název')
    popis = models.TextField(blank=True, default='', verbose_name='Popis')
    soubor = models.FileField(upload_to=knowledge_upload_path, verbose_name='Soubor')
    original_filename = models.CharField(max_length=255, blank=True, default='')
    velikost = models.PositiveIntegerField(default=0, verbose_name='Velikost v bytech')
    extracted_text = models.TextField(blank=True, default='', verbose_name='Vytěžený text')
    nahral = models.ForeignKey(
        'users.WebUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='knowledge_documents',
        verbose_name='Nahrál',
    )
    aktivni = models.BooleanField(default=True, verbose_name='Aktivní')
    vytvoreno = models.DateTimeField(auto_now_add=True)
    upraveno = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEB_KNOWLEDGE'
        verbose_name = 'Dokument znalostní báze'
        verbose_name_plural = 'Dokumenty znalostní báze'
        ordering = ['-vytvoreno']

    def __str__(self):
        return self.nazev

    def delete(self, *args, **kwargs):
        stored = self.soubor.name if self.soubor else ''
        storage = self.soubor.storage if self.soubor else None
        super().delete(*args, **kwargs)
        if stored and storage:
            storage.delete(stored)
