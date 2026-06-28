"""Pluggable parser framework for medical price sources.

Each source lives in ``parsers/sources/<name>.py`` and subclasses
``BaseParser``. Adding a source never requires touching the core
(satisfies the scalability requirement in the ТЗ).
"""
from parsers.registry import get_parser, iter_parsers, register  # noqa: F401
