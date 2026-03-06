from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.database import SessionLocal
from app import crud
from app.schemas import FileSearch


router = APIRouter(prefix="/api/export", tags=["export"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/csv")
def export_csv(
    request: Request,
    query: str | None = None,
    drive_id: int | None = None,
    drive_label: str | None = None,
    extension: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 10000,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    from datetime import datetime
    
    search = FileSearch(
        query=query,
        drive_id=drive_id,
        drive_label=drive_label,
        extension=extension,
        min_size=min_size,
        max_size=max_size,
        from_date=datetime.fromisoformat(from_date) if from_date else None,
        to_date=datetime.fromisoformat(to_date) if to_date else None,
        limit=limit,
        offset=offset,
    )
    
    files, total = crud.search_files(db, search)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["filename", "relative_path", "drive_label", "size", "created_at", "created_time", "extension"])
    
    for file in files:
        drive = crud.get_drive(db, file.drive_id)
        writer.writerow([
            file.filename,
            file.relative_path or "",
            drive.label if drive else "",
            file.size,
            file.created_at.isoformat() if file.created_at else "",
            file.created_time.isoformat() if file.created_time else "",
            file.extension or "",
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )
