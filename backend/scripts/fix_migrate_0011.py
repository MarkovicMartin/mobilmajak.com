"""Oprava chybějící users.0011 v django_migrations (lokální DB)."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()

from django.db import connection
from django.utils import timezone

name = '0011_remove_webuser_datum_upravy_alter_webuser_role'
with connection.cursor() as c:
    c.execute("SELECT 1 FROM django_migrations WHERE app=%s AND name=%s", ['users', name])
    if c.fetchone():
        print('0011 already recorded')
    else:
        c.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
            ['users', name, timezone.now()],
        )
        print('Inserted users 0011')
