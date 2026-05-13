import os
import uuid
from django.db import models


def get_ticket_image_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('ticket_images', filename)


class Ticket(models.Model):
    STAVY = [
        ('novy', 'Nový'),
        ('makam', 'Makám na tom'),
        ('opraveno', 'Opraveno'),
    ]

    id = models.AutoField(primary_key=True)
    nazev = models.CharField(max_length=200, db_column='NAZEV')
    popis = models.TextField(db_column='POPIS')
    stav = models.CharField(max_length=20, choices=STAVY, default='novy', db_column='STAV')
    autor_id = models.IntegerField(db_column='AUTOR_ID')
    autor_jmeno = models.CharField(max_length=100, db_column='AUTOR_JMENO', blank=True, default='')
    url = models.CharField(max_length=500, db_column='URL', blank=True, default='')
    opraveno_at = models.DateTimeField(null=True, blank=True, db_column='OPRAVENO_AT')
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')
    upraveno = models.DateTimeField(auto_now=True, db_column='UPRAVENO')

    class Meta:
        db_table = 'WEB_TICKETS'
        ordering = ['-vytvoreno']

    def __str__(self):
        return f"Ticket #{self.id}: {self.nazev}"


class TicketImage(models.Model):
    id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(Ticket, related_name='images', on_delete=models.CASCADE, db_column='TICKET_ID')
    obrazek = models.ImageField(upload_to=get_ticket_image_path, db_column='OBRAZEK')
    nahrano = models.DateTimeField(auto_now_add=True, db_column='NAHRANO')

    class Meta:
        db_table = 'WEB_TICKET_IMAGES'

    def __str__(self):
        return f"Image for Ticket #{self.ticket_id}"


class TicketComment(models.Model):
    id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(Ticket, related_name='comments', on_delete=models.CASCADE, db_column='TICKET_ID')
    autor_id = models.IntegerField(db_column='AUTOR_ID')
    autor_jmeno = models.CharField(max_length=100, db_column='AUTOR_JMENO', blank=True, default='')
    text = models.TextField(db_column='TEXT')
    vytvoreno = models.DateTimeField(auto_now_add=True, db_column='VYTVORENO')
    upraveno = models.DateTimeField(null=True, blank=True, db_column='UPRAVENO')

    class Meta:
        db_table = 'WEB_TICKET_COMMENTS'
        ordering = ['vytvoreno']

    def __str__(self):
        return f"Comment on Ticket #{self.ticket_id} by {self.autor_jmeno}"


class TicketUserReadState(models.Model):
    """Poslední přečtení tiketu autorem – pro nepřečtené notifikace."""

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(db_column='USER_ID')
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='read_states',
        db_column='TICKET_ID',
    )
    last_seen_at = models.DateTimeField(db_column='LAST_SEEN_AT')

    class Meta:
        db_table = 'WEB_TICKET_USER_READ'
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'ticket'], name='uniq_ticket_user_read'),
        ]

    def __str__(self):
        return f"Read state user={self.user_id} ticket={self.ticket_id}"
