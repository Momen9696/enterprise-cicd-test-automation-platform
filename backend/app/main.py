from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers.platform import router as platform_router
from app.routers.webhooks import router as webhook_router
from app.security import install_redacting_logs
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    install_redacting_logs()
    init_db()
    if get_settings().seed_on_startup:
        with SessionLocal() as session:
            seed_if_empty(session)
    yield


app = FastAPI(
    title="CI/CD Test Automation Platform",
    version="1.0.0",
    summary="Manage pipeline configuration, approved test execution, and reporting.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Hub-Signature-256", "X-Platform-Signature"],
)
app.include_router(platform_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")


@app.get("/health")
def health() -> dict:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok", "service": "cicd-test-automation-platform"}
