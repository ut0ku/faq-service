"""ASGI-конфигурация проекта FAQ Service."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faq_service.settings")

application = get_asgi_application()
