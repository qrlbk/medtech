"""Shared enumerations used across models and schemas."""
from __future__ import annotations

import enum


class ServiceCategory(str, enum.Enum):
    """High-level service categories (per ТЗ section 2.2)."""

    laboratory = "laboratory"        # лаборатория / анализы
    doctor_visit = "doctor_visit"    # приём врача
    diagnostics = "diagnostics"      # диагностика (УЗИ, МРТ, КТ ...)
    procedure = "procedure"          # процедура


class Currency(str, enum.Enum):
    KZT = "KZT"
    USD = "USD"


class MatchStatus(str, enum.Enum):
    """Status of a parsed offer in the normalization workflow."""

    pending = "pending"        # awaiting normalization
    auto = "auto"              # auto-matched above threshold
    manual = "manual"          # resolved by human
    rejected = "rejected"      # marked not a real service
