"""
Career & Skills Recommendation System — FastAPI Backend
========================================================
Production-ready REST API wrapping the 7-notebook ML pipeline.
"""

from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.engine import engine


def _load_engine_background():
    """Load ML models in a background thread so port binds immediately."""
    print("⚙️  Loading ML artifacts in background…")
    try:
        engine.load()
        print("✅  Career Intelligence Engine ready.")
    except Exception as e:
        print(f"❌  Engine load failed: {e}")


# ── Lifespan: bind port FIRST, load models in background ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=_load_engine_background, daemon=True)
    thread.start()
    yield
    print("🛑  Shutting down Career Intelligence Engine.")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - t0) * 1000:.1f}ms"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
        },
    )


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "engine_loaded": engine.is_loaded,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy" if engine.is_loaded else "loading",
        "engine": {
            "loaded":        engine.is_loaded,
            "occupations":   engine.occupation_count,
            "courses":       engine.course_count,
            "semantic_mode": engine.semantic_available,
        },
    }
