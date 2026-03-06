from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DriveBase(BaseModel):
    label: str
    serial_number: Optional[str] = None
    scan_path: Optional[str] = None
    max_depth: int = -1
    note: Optional[str] = None


class DriveCreate(DriveBase):
    pass


class DriveUpdate(BaseModel):
    label: Optional[str] = None
    serial_number: Optional[str] = None
    scan_path: Optional[str] = None
    max_depth: Optional[int] = None
    note: Optional[str] = None


class DriveResponse(DriveBase):
    id: int
    created_at: datetime
    last_scanned: Optional[datetime] = None
    total_files: int = 0
    total_size: int = 0
    total_capacity: Optional[int] = None
    available_space: Optional[int] = None

    class Config:
        from_attributes = True


class FileBase(BaseModel):
    filename: str
    relative_path: Optional[str] = None
    full_path: str
    size: Optional[int] = None
    created_at: Optional[datetime] = None
    created_time: Optional[datetime] = None
    extension: Optional[str] = ""


class FileCreate(FileBase):
    drive_id: int


class FileResponse(FileBase):
    id: int
    drive_id: int

    class Config:
        from_attributes = True


class FileSearch(BaseModel):
    query: Optional[str] = None
    drive_id: Optional[int] = None
    drive_label: Optional[str] = None
    extension: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
