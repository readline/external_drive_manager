from pathlib import Path


class Settings:
    def __init__(self):
        base = Path(__file__).parent
        self.DATABASE_PATH = base / "data" / "catalog.db"
        self.STATIC_PATH = base / "static"
        self.TEMPLATES_PATH = base / "app" / "templates"
        self.DATA_PATH = base / "data"
        
        self.STATIC_PATH.mkdir(parents=True, exist_ok=True)
        self.DATA_PATH.mkdir(parents=True, exist_ok=True)


settings = Settings()
