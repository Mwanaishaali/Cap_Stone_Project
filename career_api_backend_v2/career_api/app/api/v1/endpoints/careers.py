"""
Career recommendation endpoints.
"""
from __future__ import annotations

import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.engine import engine
from app.models.schemas import (
    CareerDetail,
    CareerSummary,
    RecommendRequest,
    RecommendResponse,
)

router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine is not yet loaded. Try again in a moment.")


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Full Career Recommendation Pipeline",
    description=(
        "Run the complete Career Intelligence pipeline: "
        "career matching → skills gap analysis → AI risk scoring → learning path generation. "
        "Supports all Kenyan education levels (CBC, 8-4-4, TVET, University)."
    ),
)
async def recommend_careers(
    request: RecommendRequest,
    _=Depends(_require_engine),
):
    t0 = time.perf_counter()
    try:
        result = engine.run_full_pipeline(
            raw_input=request.model_dump(),
            n=request.n_recommendations,
            courses_per_gap=request.courses_per_gap,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    result["meta"] = {
        "n_requested":   request.n_recommendations,
        "n_returned":    len(result["career_details"]),
        "semantic_mode": engine.semantic_available,
        "total_ms":      round((time.perf_counter() - t0) * 1000, 1),
    }
    return result


@router.post(
    "/quick",
    response_model=List[dict],
    summary="Quick Career Recommendations (summary only)",
    description="Returns a ranked summary table without gap analysis — fast response.",
)
async def quick_recommend(
    request: RecommendRequest,
    _=Depends(_require_engine),
):
    try:
        df = engine.recommend_careers(
            raw_input=request.model_dump(),
            n=request.n_recommendations,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return df.drop(columns=["_onet_code"], errors="ignore").to_dict(orient="records")


@router.get(
    "/families",
    summary="List Career Families",
    description="Return all career families in the system with occupation counts.",
)
async def list_career_families(_=Depends(_require_engine)):
    if engine.master is None:
        raise HTTPException(503, "Master data not loaded.")
    if "career_family" not in engine.master.columns:
        return {"families": []}
    counts = engine.master["career_family"].value_counts().to_dict()
    return {
        "families": [
            {"name": k, "occupation_count": v} for k, v in counts.items()
        ],
        "total_families": len(counts),
    }
