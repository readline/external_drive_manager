from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.api import drives, files, export

app = FastAPI(title="Cold Storage Drive Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_PATH)), name="static")
except Exception:
    pass

templates = Jinja2Templates(directory=str(settings.TEMPLATES_PATH))

app.include_router(drives.router)
app.include_router(files.router)
app.include_router(export.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/drives", response_class=HTMLResponse)
async def drives_page(request: Request):
    return templates.TemplateResponse("drives.html", {"request": request})


@app.get("/browse", response_class=HTMLResponse)
async def browse_page(request: Request):
    return templates.TemplateResponse("browse.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


@app.on_event("startup")
async def startup():
    from app.database import Engine
    from app.models import Base
    Base.metadata.create_all(bind=Engine)
