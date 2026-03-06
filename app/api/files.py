from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import SessionLocal
from app import crud
from app.schemas import FileResponse, FileSearch


router = APIRouter(prefix="/api/files", tags=["files"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/search", response_model=list[FileResponse])
def search_files(
    query: str | None = Query(None),
    drive_id: int | None = Query(None),
    drive_label: str | None = Query(None),
    extension: str | None = Query(None),
    min_size: int | None = Query(None),
    max_size: int | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
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
    return files


@router.get("/{file_id}", response_model=FileResponse)
def get_file(file_id: int, db: Session = Depends(get_db)):
    file = crud.get_file_by_id(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@router.get("/extensions")
def list_extensions(db: Session = Depends(get_db)):
    return {"extensions": crud.get_all_extensions(db)}
