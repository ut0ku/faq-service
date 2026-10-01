"""Небольшие вспомогательные функции для приложения FAQ."""

import inspect
from collections.abc import Iterator
from types import ModuleType


def iter_public_functions(module: ModuleType) -> Iterator[str]:
    """Возвращать описания и сигнатуры функций модуля."""
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_") or function.__module__ != module.__name__:
            continue
        description = inspect.getdoc(function) or "Нет описания"
        yield f"{name}{inspect.signature(function)} - {description}"
