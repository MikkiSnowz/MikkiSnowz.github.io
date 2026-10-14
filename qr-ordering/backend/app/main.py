import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .config import get_settings
from .database import SessionLocal
from .models import Category
from .routers import admin, public, webhooks

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# MySQL error codes -> what to do about them.
DB_HINTS = {
    1045: "MySQL rejected the username/password in DATABASE_URL (backend/.env).",
    1044: "The MySQL user in DATABASE_URL can't access that database. Create it and grant access (see README).",
    1049: "The database in DATABASE_URL doesn't exist. Create it in MySQL (see README).",
    1146: "The database tables don't exist yet. Run `python3 seed.py` in the backend folder.",
    2003: "Can't connect to MySQL. Make sure MySQL is running on the host/port in DATABASE_URL.",
}


def database_hint(exc: SQLAlchemyError) -> str:
    args = getattr(getattr(exc, "orig", None), "args", ())
    code = args[0] if args and isinstance(args[0], int) else None
    return DB_HINTS.get(code, "Database error. See the backend terminal for details.")


app = FastAPI(title="QR Ordering API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_url.rstrip("/")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(webhooks.router)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    log.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": database_hint(exc)})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Uvicorn still logs the traceback; this just gives the browser a readable message.
    return JSONResponse(
        status_code=500, content={"detail": "Server error. See the backend terminal for details."}
    )


@app.get("/api/health")
def health():
    """Open in a browser to check the backend and database are both working."""
    try:
        with SessionLocal() as db:
            has_menu = db.scalar(select(Category).limit(1)) is not None
    except SQLAlchemyError as exc:
        return JSONResponse(status_code=503, content={"ok": False, "database": database_hint(exc)})
    if not has_menu:
        return {"ok": True, "database": "connected, but the menu is empty. Run `python3 seed.py`."}
    return {"ok": True, "database": "ok"}
