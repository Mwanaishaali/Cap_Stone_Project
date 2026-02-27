"""
Course recommendation endpoints.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.engine import engine
from app.models.schemas import (
    CourseLevel,
    CourseRecommendation,
    CourseSearchRequest,
    CourseSearchResponse,
)

router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine not ready.")


@router.post(
    "/search",
    response_model=CourseSearchResponse,
    summary="Search Courses for a Skill",
    description=(
        "Find the best courses from the unified Coursera / edX / Udemy catalogue "
        "to address a specific skill gap."
    ),
)
async def search_courses(
    request: CourseSearchRequest,
    _=Depends(_require_engine),
):
    courses = engine.search_courses_for_skill(
        skill_name=request.skill_name,
        top_k=request.top_k,
        level_filter=request.level_filter.value if request.level_filter else None,
        min_quality=request.min_quality,
    )
    return CourseSearchResponse(
        courses=[CourseRecommendation(**c) for c in courses],
        query=request.skill_name,
        total_found=len(courses),
    )


@router.get(
    "/search",
    response_model=CourseSearchResponse,
    summary="Search Courses (GET)",
    description="GET version of course search — convenient for quick lookups.",
)
async def search_courses_get(
    skill: str = Query(..., description="Skill or topic to search for"),
    top_k: int = Query(5, ge=1, le=20),
    level: Optional[CourseLevel] = None,
    min_quality: float = Query(0.3, ge=0.0, le=1.0),
    _=Depends(_require_engine),
):
    courses = engine.search_courses_for_skill(
        skill_name=skill,
        top_k=top_k,
        level_filter=level.value if level else None,
        min_quality=min_quality,
    )
    return CourseSearchResponse(
        courses=[CourseRecommendation(**c) for c in courses],
        query=skill,
        total_found=len(courses),
    )


@router.get(
    "/platforms",
    summary="List Course Platforms",
    description="Return all platforms in the course catalogue with course counts.",
)
async def list_platforms(_=Depends(_require_engine)):
    if engine.courses is None:
        raise HTTPException(503, "Course catalogue not loaded.")
    counts = engine.courses["platform"].value_counts().to_dict()
    return {
        "platforms": [{"name": k, "course_count": v} for k, v in counts.items()],
        "total_courses": int(engine.courses.shape[0]),
    }


@router.get(
    "/levels",
    summary="List Course Levels",
)
async def list_levels(_=Depends(_require_engine)):
    return {
        "levels": ["Foundation", "Intermediate", "Advanced"],
        "education_level_map": engine.EDUCATION_COURSE_LEVELS,
    }
