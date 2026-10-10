"""Настроить Django перед сбором веб-тестов pytest."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faq_service.settings")
django.setup()
