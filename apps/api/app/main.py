from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import PrivateNetworkAccessMiddleware
from app.notebooks.router import router as notebooks_router
from app.notes.router import router as notes_router
from app.qdrant.client import ensure_collection
from app.sources.router import router as sources_router
from app.storage.minio_client import ensure_bucket
from app.studio.router import router as studio_router

settings = get_settings()
configure_logging(settings.app_env)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_bucket()
    except Exception:
        logger.exception("Could not ensure MinIO bucket exists on startup")
    try:
        ensure_collection()
    except Exception:
        logger.exception("Could not ensure Qdrant collection exists on startup")
    yield


app = FastAPI(title="NotebookLM Clone API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added after CORSMiddleware so it wraps it (outermost user middleware) and
# can amend its preflight response with the Private Network Access header.
app.add_middleware(PrivateNetworkAccessMiddleware)

app.include_router(auth_router)
app.include_router(notebooks_router)
app.include_router(sources_router)
app.include_router(notes_router)
app.include_router(chat_router)
app.include_router(studio_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
