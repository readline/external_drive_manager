from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

from app.database import Base


class Drive(Base):
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, unique=True, nullable=False)
    serial_number = Column(String, nullable=True)
    scan_path = Column(String, nullable=True)
    max_depth = Column(Integer, default=-1)
    note = Column(String, nullable=True)
    # Drive capacity (total size of the drive in bytes)
    total_capacity = Column(BigInteger, nullable=True)
    # Available space (free space on drive in bytes)
    available_space = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    last_scanned = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)

    files = relationship("File", back_populates="drive", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Drive(id={self.id}, label='{self.label}')>"


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)
    filename = Column(String, nullable=False)
    relative_path = Column(String, nullable=True)
    full_path = Column(String, nullable=False)
    size = Column(BigInteger)
    created_at = Column(DateTime)
    created_time = Column(DateTime)
    extension = Column(String)

    drive = relationship("Drive", back_populates="files")

    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}')>"
