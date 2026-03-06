from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import SessionLocal
from app import crud
from app.schemas import DriveCreate, DriveUpdate, DriveResponse


router = APIRouter(prefix="/api/drives", tags=["drives"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[DriveResponse])
def list_drives(offline: bool = False, db: Session = Depends(get_db)):
    return crud.list_drives(db, offline=offline)


@router.post("/", response_model=DriveResponse)
def create_drive(drive: DriveCreate, db: Session = Depends(get_db)):
    if crud.get_drive_by_label(db, drive.label):
        raise HTTPException(status_code=400, detail="Drive with this label already exists")
    return crud.create_drive(db, drive)


@router.get("/{drive_id}", response_model=DriveResponse)
def get_drive(drive_id: int, db: Session = Depends(get_db)):
    drive = crud.get_drive(db, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    return drive


@router.put("/{drive_id}", response_model=DriveResponse)
def update_drive(drive_id: int, drive: DriveUpdate, db: Session = Depends(get_db)):
    updated = crud.update_drive(db, drive_id, drive)
    if not updated:
        raise HTTPException(status_code=404, detail="Drive not found")
    return updated


@router.delete("/{drive_id}")
def delete_drive(drive_id: int, db: Session = Depends(get_db)):
    if not crud.delete_drive(db, drive_id):
        raise HTTPException(status_code=404, detail="Drive not found")
    return {"message": "Drive deleted successfully"}


@router.post("/{drive_id}/scan")
def scan_drive(drive_id: int, db: Session = Depends(get_db)):
    from app.scanner import DriveScanner
    from app import crud
    import os
    import gzip
    from pathlib import Path
    
    drive = crud.get_drive(db, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    if not drive.scan_path:
        raise HTTPException(status_code=400, detail="Drive has no scan path configured")
    
    if not os.path.exists(drive.scan_path):
        raise HTTPException(status_code=400, detail=f"Scan path does not exist: {drive.scan_path}")
    
    scanner = DriveScanner(drive.scan_path, drive.max_depth)
    files_data = scanner.scan_all()
    
    # Create gzipped scan file on the drive
    scan_file_path = Path(drive.scan_path) / "disk_scan.txt.gz"
    try:
        with gzip.open(scan_file_path, 'wt', encoding='utf-8') as f:
            # Write header comments with scan information
            f.write(f"# Disk Scan Report\n")
            f.write(f"# ================================\n")
            f.write(f"# Drive Label: {drive.label}\n")
            f.write(f"# Serial Number: {drive.serial_number or 'N/A'}\n")
            f.write(f"# Scan Path: {drive.scan_path}\n")
            f.write(f"# Max Depth: {'Unlimited' if drive.max_depth == -1 else drive.max_depth}\n")
            f.write(f"# Scan Date: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"# Total Files: {len(files_data)}\n")
            f.write(f"# Total Size: {sum(f['size'] for f in files_data)} bytes\n")
            f.write(f"# ================================\n\n")
            
            # Write table header
            f.write(f"{'Filename':<60} {'Size':>15} {'Modified':<20} {'Extension':<10} {'Path'}\n")
            f.write(f"{'-'*60} {'-'*15} {'-'*20} {'-'*10} {'-'*50}\n")
            
            # Write file entries
            for file_info in files_data:
                filename = file_info['filename'][:57] + "..." if len(file_info['filename']) > 60 else file_info['filename']
                size_str = f"{file_info['size']:,}"
                mtime_str = file_info['created_at'].strftime('%Y-%m-%d %H:%M:%S') if file_info['created_at'] else 'N/A'
                ext = file_info.get('extension', '')[:8]
                rel_path = file_info.get('relative_path', '') or '/'
                rel_path = rel_path[:47] + "..." if len(rel_path) > 50 else rel_path
                
                f.write(f"{filename:<60} {size_str:>15} {mtime_str:<20} {ext:<10} {rel_path}\n")
    except Exception as e:
        # Don't fail the scan if we can't write the file, just log it
        print(f"Warning: Could not write scan file to drive: {e}")
    
    crud.clear_drive_files(db, drive_id)
    
    batch_size = 1000
    for i in range(0, len(files_data), batch_size):
        batch = files_data[i:i + batch_size]
        crud.bulk_create_files(db, batch)
    
    last_scanned = datetime.now(timezone.utc)
    crud.update_drive_stats(db, drive_id, len(files_data), sum(f["size"] for f in files_data), last_scanned)
    
    return {"message": "Scan completed", "files_scanned": len(files_data), "scan_file": str(scan_file_path)}
