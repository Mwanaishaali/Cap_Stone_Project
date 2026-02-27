"""
Occupations catalogue endpoints — browse/search the master dataset.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.engine import engine

router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine not ready.")


@router.get(
    "/",
    summary="List All Occupations",
    description="Return all occupations in the master dataset with optional filters.",
)
async def list_occupations(
    career_family: Optional[str] = Query(None),
    min_education: Optional[str] = Query(None),
    demand_level:  Optional[str] = Query(None, description="High | Medium | Low"),
    search:        Optional[str] = Query(None, description="Fuzzy search by occupation name"),
    limit:         int           = Query(50, ge=1, le=500),
    offset:        int           = Query(0, ge=0),
    _=Depends(_require_engine),
):
    if engine.master is None:
        raise HTTPException(503, "Master data not loaded.")

    df = engine.master.copy()

    if career_family:
        df = df[df["career_family"].str.lower() == career_family.lower()]
    if min_education:
        df = df[df["min_education"].str.lower() == min_education.lower()]
    if demand_level and "demand_level" in df.columns:
        df = df[df["demand_level"].str.lower() == demand_level.lower()]
    if search:
        df = df[df["occupation"].str.contains(search, case=False, na=False)]

    total = len(df)
    df = df.iloc[offset: offset + limit]

    keep = [c for c in [
        "occupation", "career_family", "job_zone", "min_education",
        "demand_level", "future_proof_score", "median_wage_2022"
    ] if c in df.columns]

    return {
        "occupations": df[keep].to_dict(orient="records"),
        "total":       total,
        "offset":      offset,
        "limit":       limit,
    }


@router.get(
    "/{occupation_name}",
    summary="Get Occupation Details",
    description="Return full profile for a single occupation.",
)
async def get_occupation(
    occupation_name: str,
    _=Depends(_require_engine),
):
    if engine.master is None:
        raise HTTPException(503)

    occ = engine.master[
        engine.master["occupation"].str.lower() == occupation_name.lower()
    ]
    if occ.empty:
        occ = engine.master[
            engine.master["occupation"].str.contains(
                occupation_name.split()[0], case=False, na=False
            )
        ]
    if occ.empty:
        raise HTTPException(404, f"Occupation '{occupation_name}' not found.")

    row = occ.iloc[0]

    # Risk info
    risk_col     = "blended_risk" if "blended_risk" in row.index else "automation_risk"
    risk_score   = float(row.get(risk_col, 0.45))
    risk_label   = engine.categorise_risk(risk_score)

    # Skill profile
    skill_profile = {
        col.replace("skill_", "").replace("_", " ").title(): round(float(row.get(col, 0)), 2)
        for col in engine.SKILL_COLS
        if row.get(col, 0) > 0
    }

    return {
        "occupation":         row.get("occupation"),
        "onet_code":          row.get("onet_code", ""),
        "career_family":      row.get("career_family", ""),
        "job_zone":           int(row.get("job_zone", 0)),
        "min_education":      row.get("min_education", ""),
        "demand_level":       row.get("demand_level", ""),
        "median_wage_2022":   row.get("median_wage_2022", None),
        "employment_change_pct": row.get("employment_change_pct", None),
        "future_proof_score": float(row.get("future_proof_score", 50)),
        "ai_risk": {
            "score":       round(risk_score * 100, 1),
            "label":       risk_label,
            "explanation": engine.RISK_EXPLANATIONS.get(risk_label, ""),
        },
        "skill_profile": skill_profile,
    }
