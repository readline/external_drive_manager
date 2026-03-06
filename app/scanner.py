import os
from pathlib import Path
from datetime import datetime
from typing import Iterator

from app.models import File


class DriveScanner:
    def __init__(self, scan_path: str, max_depth: int = -1):
        self.scan_path = Path(scan_path).resolve()
        self.max_depth = max_depth

    def get_depth(self, path: Path) -> int:
        try:
            relative = path.relative_to(self.scan_path)
            return len(relative.parts)
        except ValueError:
            return 0

    def should_scan(self, path: Path) -> bool:
        if self.max_depth == -1:
            return True
        return self.get_depth(path) <= self.max_depth

    def scan(self) -> Iterator[dict]:
        for root, dirs, files in os.walk(self.scan_path):
            root_path = Path(root)
            
            if not self.should_scan(root_path):
                dirs.clear()
                continue
            
            for filename in files:
                file_path = root_path / filename
                
                try:
                    stat = file_path.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    ctime = datetime.fromtimestamp(stat.st_ctime)
                    
                    relative_path = root_path.relative_to(self.scan_path)
                    
                    yield {
                        "filename": filename,
                        "relative_path": str(relative_path) if str(relative_path) != "." else None,
                        "full_path": str(file_path),
                        "size": stat.st_size,
                        "created_at": mtime,
                        "created_time": ctime,
                        "extension": Path(filename).suffix.lower(),
                    }
                except (OSError, PermissionError):
                    continue

    def scan_all(self) -> list[dict]:
        return list(self.scan())
