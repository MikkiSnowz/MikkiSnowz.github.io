import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import admin, public, webhooks

logging.basicConfig(level=logging.INFO)

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


@app.get("/api/health")
def health():
    return {"ok": True}
