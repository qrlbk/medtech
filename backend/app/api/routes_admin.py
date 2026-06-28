"""Admin endpoints: unmatched-queue review, manual triggering, file upload."""
from __future__ import annotations

import base64
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.db.session import SessionLocal
from app.models import User
from app.schemas.admin import IngestTriggerOut, ResolveIn, UnmatchedItem
from app.services import admin_review
from app.services.ingest import persist_offers, persist_raw_doc
from app.services.normalization import normalize_pending
from parsers.base import RawDoc
from parsers.documents import DocumentError, extract_rows, format_from_filename
from parsers.file_base import offers_from_rows

router = APIRouter(prefix="/admin", tags=["admin"])

# Guard rail: reject absurdly large uploads (price lists are small documents).
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.get("/unmatched", response_model=list[UnmatchedItem])
def unmatched(
    limit: int = 50, offset: int = 0,
    _: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    return admin_review.list_unmatched(db, limit, offset)


@router.post("/unmatched/{queue_id}/resolve")
def resolve(
    queue_id: uuid.UUID, payload: ResolveIn,
    _: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    ok = admin_review.resolve(db, queue_id, payload.catalog_id, payload.add_as_synonym)
    if not ok:
        raise HTTPException(404, "Queue item not found")
    return {"status": "resolved"}


def _run_pipeline_bg(sources: list[str] | None) -> None:
    from pipelines.core import run_pipeline

    with SessionLocal() as db:
        run_pipeline(db, sources)


@router.post("/ingest", response_model=IngestTriggerOut)
def trigger_ingest(
    background: BackgroundTasks, source: str | None = None,
    _: User = Depends(get_current_admin),
):
    """Manually trigger parsing (ТЗ 3.1: запуск парсинга вручную через интерфейс)."""
    sources = [source] if source else None
    background.add_task(_run_pipeline_bg, sources)
    return IngestTriggerOut(
        status="started",
        detail=f"Pipeline triggered for {'all sources' if not source else source}",
    )


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    clinic: str = Form(...),
    city: str = Form(...),
    source: str = Form("upload"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Parse a price list uploaded from the user's device (PDF/DOCX/XLSX/XLS).

    Implements ТЗ 3.1: clinics often publish prices as office documents. The
    file is stored verbatim in the raw layer, extracted with the shared column
    heuristics, then normalized like any other source.
    """
    fmt = format_from_filename(file.filename or "")
    if fmt is None:
        raise HTTPException(
            400, "Неподдерживаемый формат. Допустимо: PDF, DOCX, XLSX, XLS."
        )
    data = await file.read()
    if not data:
        raise HTTPException(400, "Пустой файл.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Файл слишком большой (максимум 20 МБ).")

    try:
        rows = extract_rows(data, fmt)
    except DocumentError as exc:
        raise HTTPException(422, f"Не удалось разобрать документ: {exc}") from exc

    url = f"upload://{file.filename}"
    offers = list(
        offers_from_rows(
            rows, source=source, clinic=clinic.strip(), city=city.strip(),
            source_url=url,
        )
    )
    if not offers:
        raise HTTPException(
            422, "В документе не найдено строк с услугой и ценой."
        )

    raw = persist_raw_doc(
        db,
        RawDoc(
            source=source, url=url, content_type=fmt,
            payload=base64.b64encode(data).decode("ascii"),
        ),
    )
    new = persist_offers(db, offers, raw)
    db.commit()
    stats = normalize_pending(db)

    return {
        "filename": file.filename,
        "format": fmt,
        "clinic": clinic.strip(),
        "city": city.strip(),
        "rows": len(rows),
        "offers_found": len(offers),
        "offers_new": new,
        "auto_matched": stats.auto_matched,
        "unmatched": stats.unmatched,
        "prices_created": stats.prices_created,
    }
