import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import User, ImportRun
from app.services.dry_run_service import execute_bzp_dry_run
from app.services.importer import import_notices
from app.importers.bzp_client import fetch_all_bzp_notices

router = APIRouter()

@router.post("/tenders/dry-run")
def bzp_dry_run_endpoint(
    notice_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_pages: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return execute_bzp_dry_run(
        db=db,
        notice_type=notice_type,
        date_from=date_from,
        date_to=date_to,
        max_pages=max_pages,
        page_size=page_size
    )

@router.post("/tenders")
def run_live_import(
    notice_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_pages: Optional[int] = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import_run = ImportRun(
        tenant_id=current_user.tenant_id,
        source_system="BZP",
        status="PENDING",
        params={
            "notice_type": notice_type,
            "date_from": date_from,
            "date_to": date_to,
            "max_pages": max_pages,
            "page_size": page_size
        }
    )
    db.add(import_run)
    db.commit()
    db.refresh(import_run)

    raw_notices = fetch_all_bzp_notices(
        notice_type=notice_type,
        publication_date_from=date_from,
        publication_date_to=date_to,
        max_pages=max_pages,
        page_size=page_size
    )

    stats = import_notices(
        db=db,
        tenant_id=current_user.tenant_id,
        raw_notices=raw_notices,
        import_run_id=import_run.id
    )

    return {
        "import_run_id": str(import_run.id),
        "status": import_run.status,
        "statistics": stats
    }

@router.get("/runs")
def list_import_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ImportRun).filter(ImportRun.tenant_id == current_user.tenant_id).order_by(ImportRun.started_at.desc()).all()

@router.get("/runs/{import_run_id}")
def get_import_run(
    import_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(ImportRun).filter(ImportRun.id == import_run_id, ImportRun.tenant_id == current_user.tenant_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import run not found")
    return run
