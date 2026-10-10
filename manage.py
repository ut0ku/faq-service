#!/usr/bin/env python
"""Командная строка Django для проекта FAQ Service."""

import os
import sys


def main() -> None:
    """Выполнить команду управления Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faq_service.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        raise ImportError(
            "Django не установлен. Установите зависимости командой "
            "'pip install -r requirements.txt'."
        ) from error
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
