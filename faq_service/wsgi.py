"""WSGI-конфигурация проекта FAQ Service."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faq_service.settings")

application = get_wsgi_application()
