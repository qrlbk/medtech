"""Source parser registry.

Sources self-register via the ``@register`` decorator. ``load_all`` imports
every module in ``parsers/sources`` so decorators run.
"""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterator

from parsers.base import BaseParser

_REGISTRY: dict[str, type[BaseParser]] = {}


def register(cls: type[BaseParser]) -> type[BaseParser]:
    if not cls.source:
        raise ValueError(f"{cls.__name__} must define a non-empty `source`")
    _REGISTRY[cls.source] = cls
    return cls


def _load_all() -> None:
    import parsers.sources as sources_pkg

    for mod in pkgutil.iter_modules(sources_pkg.__path__):
        importlib.import_module(f"parsers.sources.{mod.name}")


def get_parser(source: str, offline: bool | None = None) -> BaseParser:
    _load_all()
    if source not in _REGISTRY:
        raise KeyError(f"Unknown source: {source}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[source](offline=offline)


def iter_parsers() -> Iterator[BaseParser]:
    _load_all()
    for cls in _REGISTRY.values():
        yield cls()


def known_sources() -> list[str]:
    _load_all()
    return sorted(_REGISTRY)
