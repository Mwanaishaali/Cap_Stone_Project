"""
AI risk scoring endpoints — wrapping Notebook 05.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.engine import engine
from app.models.schemas import RiskCategory, RiskRequest, RiskResponse

router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine not ready.")


@router.post(
    "/score",
    response_model=RiskResponse,
    summary="AI Risk Score for an Occupation",
    description=(
        "Compute the AI replacement risk score for a specific occupation. "
        "Blends BLS automation data (where available) with O*NET skill-based risk estimation."
    ),
)
async def get_risk_score(
    request: RiskRequest,
    _=Depends(_require_engine),
):
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
        raise HTTPException(404, f"Occupation '{request.occupation}' not found.")

    row           = occ.iloc[0]
    blended_risk  = float(row.get("blended_risk", row.get("automation_risk", 0.45)))
    risk_label    = engine.categorise_risk(blended_risk)
    fp_score      = float(row.get("future_proof_score", 50.0))

    return RiskResponse(
        occupation=str(row.get("occupation", request.occupation)),
        ai_risk_score=round(blended_risk * 100, 1),
        ai_risk_label=risk_label,
        future_proof_score=fp_score,
        risk_explanation=engine.RISK_EXPLANATIONS.get(risk_label, ""),
        mitigation_advice=engine.get_risk_mitigation(risk_label),
    )


@router.get(
    "/score",
    response_model=RiskResponse,
    summary="AI Risk Score (GET)",
)
async def get_risk_score_get(
    occupation: str = Query(..., description="Occupation name"),
    _=Depends(_require_engine),
):
    return await get_risk_score(RiskRequest(occupation=occupation))


@router.get(
    "/leaderboard",
    summary="Future-Proof Career Leaderboard",
    description=(
        "Return the top careers ranked by future-proof score "
        "(composite of demand, AI risk shield, and salary)."
    ),
)
async def future_proof_leaderboard(
    top_n: int = Query(20, ge=1, le=100),
    career_family: Optional[str] = Query(None, description="Filter by career family"),
    risk_max: Optional[RiskCategory] = Query(None, description="Filter by max risk category"),
    _=Depends(_require_engine),
):
    if engine.master is None:
        raise HTTPException(503, "Master data not loaded.")

    df = engine.master.copy()
    if career_family:
        df = df[df["career_family"].str.lower() == career_family.lower()]
    if risk_max and "risk_category" in df.columns:
        risk_order = {"Low": 0, "Medium": 1, "High": 2, "Very High": 3}
        max_level  = risk_order.get(risk_max.value, 3)
        df = df[df["risk_category"].map(risk_order).fillna(3) <= max_level]

    if "future_proof_score" not in df.columns:
        df["future_proof_score"] = 50.0

    top = df.nlargest(top_n, "future_proof_score")[
        ["occupation", "career_family", "future_proof_score",
         "blended_risk" if "blended_risk" in df.columns else "automation_risk",
         "demand_level", "median_wage_2022"]
    ].copy()

    risk_col = "blended_risk" if "blended_risk" in top.columns else "automation_risk"
    records = []
    for _, row in top.iterrows():
        records.append({
            "occupation":         row["occupation"],
            "career_family":      row.get("career_family", ""),
            "future_proof_score": round(float(row.get("future_proof_score", 50)), 1),
            "ai_risk_score":      round(float(row.get(risk_col, 0.45)) * 100, 1),
            "ai_risk_label":      engine.categorise_risk(float(row.get(risk_col, 0.45))),
            "demand_level":       row.get("demand_level", ""),
            "median_wage":        row.get("median_wage_2022", None),
        })

    return {
        "leaderboard":  records,
        "total_shown":  len(records),
        "filters_applied": {
            "career_family": career_family,
            "risk_max":      risk_max.value if risk_max else None,
        },
    }


@router.get(
    "/distribution",
    summary="Risk Distribution across all Occupations",
)
async def risk_distribution(_=Depends(_require_engine)):
    if engine.master is None:
        raise HTTPException(503)

    risk_col = "blended_risk" if "blended_risk" in engine.master.columns else "automation_risk"
    categories = engine.master[risk_col].apply(engine.categorise_risk).value_counts().to_dict()

    return {
        "distribution": {k: int(v) for k, v in categories.items()},
        "total_occupations": int(engine.master.shape[0]),
        "thresholds":  engine.RISK_THRESHOLDS,
    }
