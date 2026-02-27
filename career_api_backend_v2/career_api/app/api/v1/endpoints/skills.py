"""
Skills gap analysis endpoints.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from app.core.engine import engine
from app.models.schemas import (
    GapReport,
    LearningPath,
    SkillsGapRequest,
    SkillsGapResponse,
    UserType,
)

router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine not ready.")


@router.post(
    "/gap",
    response_model=SkillsGapResponse,
    summary="Skills Gap Analysis",
    description=(
        "Analyse the gap between a user's current skills and the requirements of a "
        "target occupation, using O*NET skill dimensions. Returns ranked gaps, "
        "strengths, and alignment score."
    ),
)
async def analyse_gap(
    request: SkillsGapRequest,
    include_learning_path: bool = True,
    courses_per_gap: int = 2,
    _=Depends(_require_engine),
):
    t0 = time.perf_counter()

    # Build a minimal raw_input for skill parsing
    raw_input = {
        "skills":    request.user_skills,
        "user_type": request.user_type.value,
    }
    user_skill_scores = engine.parse_user_skills(raw_input)

    # Find occupation in master
    occ = engine.master[
        engine.master["occupation"].str.lower() == request.occupation.lower()
    ]
    if occ.empty:
        occ = engine.master[
            engine.master["occupation"].str.contains(
                request.occupation.split()[0], case=False, na=False
            )
        ]
    if occ.empty:
        raise HTTPException(
            404, f"Occupation '{request.occupation}' not found. "
                 f"Use GET /api/v1/occupations to list available occupations."
        )

    occ_row    = occ.iloc[0]
    gap_report = engine.analyse_skills_gap(
        user_skill_scores, occ_row,
        top_n_gaps=request.top_n_gaps,
        top_n_strong=request.top_n_strong,
    )

    learning_path = None
    if include_learning_path:
        learning_path = engine.generate_learning_path(
            gap_report,
            user_type=request.user_type.value,
            courses_per_gap=courses_per_gap,
        )

    return SkillsGapResponse(
        gap_report=GapReport(**gap_report),
        learning_path=LearningPath(**learning_path) if learning_path else None,
        pipeline_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@router.get(
    "/dimensions",
    summary="List O*NET Skill Dimensions",
    description="Return all 35 O*NET skill dimensions used in gap analysis.",
)
async def list_skill_dimensions(_=Depends(_require_engine)):
    return {
        "skill_dimensions": [
            {
                "col":         col,
                "name":        col.replace("skill_", "").replace("_", " ").title(),
                "description": engine.CANONICAL_SKILLS.get(col, ""),
            }
            for col in engine.SKILL_COLS
        ],
        "total": len(engine.SKILL_COLS),
    }
