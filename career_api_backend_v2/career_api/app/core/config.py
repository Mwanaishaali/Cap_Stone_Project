"""Application configuration — reads from environment variables."""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Project metadata ──────────────────────────────────────────────────────
    PROJECT_NAME: str = "Career & Skills Recommendation System"
    PROJECT_DESCRIPTION: str = (
        "AI-powered career recommendations, skills gap analysis, "
        "AI risk scoring, and personalised learning paths. "
        "Tailored for the Kenyan education system (CBC, 8-4-4, TVET, University)."
    )
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["*"]  # Restrict in production

    # ── File paths (resolved relative to project root) ────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent  # Cap_Stone_Project/
    ARTIFACTS_DIR: Path = BASE_DIR.parent / "artifacts"
    PROCESSED_DIR: Path = BASE_DIR.parent / "DATA" / "processed"
    MODEL_DIR: Path = BASE_DIR.parent / "models"

    # ── Model settings ────────────────────────────────────────────────────────
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    DEFAULT_RECOMMENDATIONS: int = 5
    MAX_RECOMMENDATIONS: int = 20
    DEFAULT_COURSES_PER_GAP: int = 2
    MAX_COURSES_PER_GAP: int = 5

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
