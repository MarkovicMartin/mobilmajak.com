import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings_vallora")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
