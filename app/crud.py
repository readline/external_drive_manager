from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
import fnmatch

from app.models import Drive, File
from app.schemas import DriveCreate, DriveUpdate, FileSearch


def create_drive(db: Session, drive: DriveCreate) -> Drive:
    db_drive = Drive(
        label=drive.label,
        serial_number=drive.serial_number,
        scan_path=drive.scan_path,
        max_depth=drive.max_depth,
        note=drive.note,
    )
    db.add(db_drive)
    db.commit()
    db.refresh(db_drive)
    return db_drive


def update_drive_note(db: Session, drive_id: int, note: str | None) -> Drive | None:
    db_drive = get_drive(db, drive_id)
    if not db_drive:
        return None
    
    db_drive.note = note
    db.commit()
    db.refresh(db_drive)
    return db_drive


def get_drive(db: Session, drive_id: int) -> Drive | None:
    return db.query(Drive).filter(Drive.id == drive_id).first()


def get_drive_by_label(db: Session, label: str) -> Drive | None:
    return db.query(Drive).filter(Drive.label == label).first()


def list_drives(db: Session, offline: bool = False) -> list[Drive]:
    query = db.query(Drive)
    if offline:
        query = query.filter(Drive.last_scanned.is_(None))
    return query.all()


def update_drive(db: Session, drive_id: int, drive: DriveUpdate) -> Drive | None:
    db_drive = get_drive(db, drive_id)
    if not db_drive:
        return None
    
    update_data = drive.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_drive, field, value)
    
    db.commit()
    db.refresh(db_drive)
    return db_drive


def delete_drive(db: Session, drive_id: int) -> bool:
    db_drive = get_drive(db, drive_id)
    if not db_drive:
        return False
    db.delete(db_drive)
    db.commit()
    return True


def update_drive_stats(db: Session, drive_id: int, total_files: int, total_size: int, last_scanned: datetime) -> Drive | None:
    db_drive = get_drive(db, drive_id)
    if not db_drive:
        return None
    
    db_drive.total_files = total_files
    db_drive.total_size = total_size
    db_drive.last_scanned = last_scanned
    db.commit()
    db.refresh(db_drive)
    return db_drive


def update_drive_capacity(db: Session, drive_id: int, total_capacity: int, available_space: int) -> Drive | None:
    db_drive = get_drive(db, drive_id)
    if not db_drive:
        return None
    
    db_drive.total_capacity = total_capacity
    db_drive.available_space = available_space
    db.commit()
    db.refresh(db_drive)
    return db_drive


def create_file(db: Session, file_data: dict) -> File:
    db_file = File(**file_data)
    db.add(db_file)
    return db_file


def bulk_create_files(db: Session, files: list[dict]) -> list[File]:
    db_files = [File(**f) for f in files]
    db.bulk_save_objects(db_files)
    return db_files


def clear_drive_files(db: Session, drive_id: int) -> int:
    count = db.query(File).filter(File.drive_id == drive_id).delete()
    db.commit()
    return count


def search_files(db: Session, search: FileSearch) -> tuple[list[File], int]:
    query = db.query(File)
    
    if search.query:
        wildcard_pattern = search.query.replace("*", "%").replace("?", "_")
        # Search in filename, relative_path, and full_path
        query = query.filter(
            or_(
                File.filename.like(f"%{wildcard_pattern}%"),
                File.relative_path.like(f"%{wildcard_pattern}%"),
                File.full_path.like(f"%{wildcard_pattern}%")
            )
        )
    
    if search.drive_id:
        query = query.filter(File.drive_id == search.drive_id)
    
    if search.drive_label:
        query = query.join(Drive).filter(Drive.label == search.drive_label)
    
    if search.extension:
        # Normalize extension - add dot if missing
        ext = search.extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        query = query.filter(File.extension == ext)
    
    if search.min_size is not None:
        query = query.filter(File.size >= search.min_size)
    
    if search.max_size is not None:
        query = query.filter(File.size <= search.max_size)
    
    if search.from_date:
        query = query.filter(File.created_at >= search.from_date)
    
    if search.to_date:
        query = query.filter(File.created_at <= search.to_date)
    
    total = query.count()
    files = query.order_by(File.created_at.desc()).offset(search.offset).limit(search.limit).all()
    
    return files, total


def get_file_by_id(db: Session, file_id: int) -> File | None:
    return db.query(File).filter(File.id == file_id).first()


def get_all_extensions(db: Session) -> list[str]:
    return [row[0] for row in db.query(File.extension).distinct().filter(File.extension.isnot(None)).all()]


def get_stats(db: Session) -> dict:
    total_drives = db.query(Drive).count()
    total_files = db.query(File).count()
    total_size = db.query(func.sum(File.size)).scalar() or 0
    
    return {
        "total_drives": total_drives,
        "total_files": total_files,
        "total_size": total_size,
    }
