"""Import the official services reference (`Справочник услуг.xlsx`) into the catalog.

The hackathon organizers ship a reference workbook with ~1.3k canonical medical
services. Columns: ID, Специальность, Code, Name_ru, TarificatrCode.

This importer maps each ``Name_ru`` to a normalized :class:`ServiceCatalog`
entry, infers a ТЗ category from the name/specialty, and registers synonyms so
the matcher can link raw clinic-site names to the official dictionary. It is
idempotent (keyed on the normalized name) and reuses the same Excel extractor
as the price-list parsers.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ServiceCatalog, ServiceSynonym
from app.models.enums import ServiceCategory
from app.services.text import normalize_text

logger = logging.getLogger(__name__)

DATA_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "services_catalog_official.xlsx"
)

_VISIT_PREFIXES = ("прием", "приём", "консультац", "осмотр", "повторный прием")
_DIAGNOSTIC_KW = (
    "узи", "мрт", "кт ", "компьютерная томограф", "рентген", "ренгено", "флюорограф",
    "томограф", "эндоскоп", "гастроскоп", "фгдс", "фгс", "колоноскоп", "ректоскоп",
    "маммограф", "денситометр", "доплер", "допплер", "эхокардиограф", "эхокг", "экг",
    "ээг", "эмг", "спирограф", "спирометр", "аудиометр", "кардиотокограф", "ктг",
    "сцинтиграф", "биопси", "пункци",
)
_LAB_KW = (
    "анализ", "кров", "моч", "посев", "мазк", "соскоб", "цитолог", "гистолог",
    "биохим", "гормон", "антитела", "пцр", "маркер", "иммуноглобулин", "igg", "igm",
)
_LAB_SPECIALTIES = ("лаборатория", "лабораторная диагностика")


def infer_category(name: str, specialty: str | None) -> ServiceCategory:
    low = name.lower()
    spec = (specialty or "").lower()
    if low.startswith(_VISIT_PREFIXES):
        return ServiceCategory.doctor_visit
    if any(kw in low for kw in _DIAGNOSTIC_KW):
        return ServiceCategory.diagnostics
    if any(kw in spec for kw in _LAB_SPECIALTIES) or any(kw in low for kw in _LAB_KW):
        return ServiceCategory.laboratory
    return ServiceCategory.procedure


def import_official_catalog(db: Session, path: Path | None = None) -> int:
    """Load the official xlsx reference. Returns the number of new services."""
    from parsers.documents import extract_xlsx_rows

    path = path or DATA_FILE
    if not path.exists():
        logger.info("Official catalog not found at %s; skipping import", path)
        return 0

    rows = extract_xlsx_rows(path.read_bytes())
    if not rows:
        return 0

    header = [c.lower() for c in rows[0]]
    try:
        spec_i = header.index("специальность")
        name_i = header.index("name_ru")
    except ValueError:
        # Fall back to the documented column order if headers differ.
        spec_i, name_i = 1, 3

    # Cache existing names to keep the import idempotent without N queries.
    existing_names = {
        n for (n,) in db.execute(select(ServiceCatalog.name_norm)).all()
    }
    created = 0
    seen: set[str] = set()
    for row in rows[1:]:
        if name_i >= len(row):
            continue
        name = row[name_i].strip()
        specialty = row[spec_i].strip() if spec_i < len(row) else None
        if not name:
            continue
        key = normalize_text(name)
        if not key or key in seen:
            continue
        seen.add(key)

        svc = db.scalar(
            select(ServiceCatalog).where(ServiceCatalog.name_norm == name)
        ) if name in existing_names else None
        if svc is None:
            svc = ServiceCatalog(name_norm=name, category=infer_category(name, specialty))
            db.add(svc)
            db.flush()
            created += 1
            existing_names.add(name)

        _add_synonyms(db, svc, name, specialty)

    db.commit()
    total = db.scalar(select(func.count(ServiceCatalog.id)))
    logger.info("Official catalog imported: +%d services (total now %d)", created, total)
    return created


def _add_synonyms(
    db: Session, svc: ServiceCatalog, name: str, specialty: str | None
) -> None:
    existing = {
        s.alias_norm
        for s in db.scalars(
            select(ServiceSynonym).where(ServiceSynonym.catalog_id == svc.id)
        )
    }
    aliases = [name]
    # For doctor visits, the bare specialty is a common raw form ("Кардиолог").
    if svc.category == ServiceCategory.doctor_visit and specialty:
        aliases.append(specialty)
    for alias in aliases:
        alias_norm = normalize_text(alias)
        if not alias_norm or alias_norm in existing:
            continue
        db.add(
            ServiceSynonym(
                catalog_id=svc.id, alias=alias, alias_norm=alias_norm, lang="ru"
            )
        )
        existing.add(alias_norm)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with SessionLocal() as db:
        import_official_catalog(db)


if __name__ == "__main__":
    main()
