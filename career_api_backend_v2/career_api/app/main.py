"""
Career & Skills Recommendation System — FastAPI Backend
========================================================
Production-ready REST API wrapping the 7-notebook ML pipeline.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.engine import engine


# ── Lifespan: load all ML artifacts once at startup ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup; release on shutdown."""
    print("⚙️  Loading ML artifacts…")
    engine.load()
    print("✅  Career Intelligence Engine ready.")
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
    allow_origins=["*"],          # allow all origins including file://
    allow_credentials=False,      # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - t0) * 1000:.1f}ms"
    return response


# ── Global exception handler ──────────────────────────────────────────────────
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


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Root health check ─────────────────────────────────────────────────────────
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
        "status": "healthy",
        "engine": {
            "loaded": engine.is_loaded,
            "occupations": engine.occupation_count,
            "courses": engine.course_count,
            "semantic_mode": engine.semantic_available,
        },
    }
