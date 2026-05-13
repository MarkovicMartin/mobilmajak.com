"""Otestuje webhook - spusť: python manage.py test_webhook"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Otestuje odeslání na N8N webhook'

    def handle(self, *args, **options):
        urls = getattr(settings, 'TICKET_WEBHOOK_URLS', [])
        self.stdout.write(f'Webhooky: {urls}')
        if not urls:
            self.stdout.write(self.style.ERROR('TICKET_WEBHOOK_URLS není nastaveno!'))
            return

        import requests
        payload = {'event': 'test', 'ticket_id': 0, 'nazev': 'Test', 'autor_jmeno': 'Test'}
        for url in urls:
            try:
                r = requests.post(url, json=payload, timeout=15, verify=False)
                self.stdout.write(self.style.SUCCESS(f'{url}: {r.status_code}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'{url}: {e}'))
