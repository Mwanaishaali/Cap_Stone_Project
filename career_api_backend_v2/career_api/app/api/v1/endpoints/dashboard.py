"""
Dashboard endpoint — aggregated data for charts and sector insights.
Covers: career demand vs AI risk, sector summaries, emerging careers by track/pathway.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.engine import engine


def _sf(val, default=0.0):
    """
    Safe float: convert any value to a JSON-safe Python float.
    Replaces NaN, Inf, None, and non-numeric values with `default`.
    Must be called on EVERY numeric value read from the DataFrame
    before placing it in the response dict — otherwise Python's
    json.dumps() raises: ValueError: Out of range float values are
    not JSON compliant.
    """
    if val is None:
        return default
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _sanitise_dict(obj):
    """
    Recursively walk a dict/list and replace every NaN/Inf float with 0.0.
    Applied to the entire response as a final safety net before returning.
    """
    if isinstance(obj, dict):
        return {k: _sanitise_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitise_dict(v) for v in obj]
    if isinstance(obj, float):
        return 0.0 if (np.isnan(obj) or np.isinf(obj)) else obj
    if isinstance(obj, np.floating):
        v = float(obj)
        return 0.0 if (np.isnan(v) or np.isinf(v)) else v
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


router = APIRouter()


def _require_engine():
    if not engine.is_loaded:
        raise HTTPException(503, "ML engine not ready.")


@router.get(
    "/",
    summary="Full Dashboard Data",
    description=(
        "Returns all data needed to render the dashboard: "
        "sector risk summary, demand distribution, top future-proof careers, "
        "emerging careers, and AI risk breakdown."
    ),
)
async def get_dashboard(
    user_type: Optional[str] = Query(None, description="Filter by user type (cbc, 8-4-4, graduate, professional)"),
    track: Optional[str] = Query(None, description="CBC track filter"),
    pathway: Optional[str] = Query(None, description="CBC pathway filter"),
    career_family: Optional[str] = Query(None, description="Filter by career family"),
    _=Depends(_require_engine),
):
    if engine.master is None:
        raise HTTPException(503, "Master data not loaded.")

    df = engine.master.copy()

    # ── Apply filters ─────────────────────────────────────────────────────────
    if career_family:
        df = df[df["career_family"].str.lower() == career_family.lower()]

    if user_type and "job_zone" in df.columns:
        allowed_zones = engine.USER_TYPE_JOB_ZONES.get(user_type.lower(), [1, 2, 3, 4, 5])
        df = df[df["job_zone"].isin(allowed_zones)]

    if df.empty:
        df = engine.master.copy()

    risk_col = "blended_risk" if "blended_risk" in df.columns else "automation_risk"

    # ── 1. Sector risk summary ────────────────────────────────────────────────
    sector_risk = []
    if "career_family" in df.columns:
        for family, group in df.groupby("career_family"):
            avg_risk = _sf(
                group[risk_col].mean() if risk_col in group.columns else 0.45,
                default=0.45
            )
            avg_fp = _sf(
                group["future_proof_score"].mean()
                if "future_proof_score" in group.columns else 50.0,
                default=50.0
            )
            demand_mode = (
                group["demand_level"].mode()[0]
                if "demand_level" in group.columns and not group.empty
                else "Medium"
            )
            sector_risk.append({
                "career_family":    str(family),
                "avg_ai_risk":      round(avg_risk * 100, 1),
                "avg_future_proof": round(avg_fp, 1),
                "dominant_demand":  str(demand_mode),
                "occupation_count": int(len(group)),
                "risk_label":       engine.categorise_risk(avg_risk),
                "risk_color":       engine.RISK_COLORS.get(
                                        engine.categorise_risk(avg_risk), "#95a5a6"
                                    ),
            })
        sector_risk.sort(key=lambda x: x["avg_future_proof"], reverse=True)

    # ── 2. Demand distribution ────────────────────────────────────────────────
    demand_dist = {}
    if "demand_level" in df.columns:
        counts = df["demand_level"].value_counts().to_dict()
        demand_dist = {k: int(v) for k, v in counts.items()}

    # ── 3. AI risk distribution ───────────────────────────────────────────────
    risk_dist = {}
    if risk_col in df.columns:
        cats = df[risk_col].apply(engine.categorise_risk).value_counts().to_dict()
        risk_dist = {k: int(v) for k, v in cats.items()}

    # ── 4. Scatter data: AI Risk vs Future-Proof ──────────────────────────────
    scatter_data = []
    if risk_col in df.columns and "future_proof_score" in df.columns:
        sample = df.dropna(subset=[risk_col]).head(100)
        for _, row in sample.iterrows():
            mw = _sf(row.get("median_wage_2022"), default=None)
            scatter_data.append({
                "occupation":    str(row.get("occupation", "")),
                "career_family": str(row.get("career_family", "")),
                "ai_risk":       round(_sf(row[risk_col]) * 100, 1),
                "future_proof":  round(_sf(row.get("future_proof_score"), 50.0), 1),
                "demand_level":  str(row.get("demand_level") or "Medium"),
                "median_wage":   mw,
            })

    # ── 5. Top future-proof careers ───────────────────────────────────────────
    top_careers = []
    if "future_proof_score" in df.columns:
        top = df.nlargest(10, "future_proof_score")
        for _, row in top.iterrows():
            risk_score = _sf(row.get(risk_col), 0.45)
            mw = _sf(row.get("median_wage_2022"), default=None)
            top_careers.append({
                "occupation":         str(row.get("occupation", "")),
                "career_family":      str(row.get("career_family", "")),
                "future_proof_score": round(_sf(row.get("future_proof_score"), 50.0), 1),
                "ai_risk_score":      round(risk_score * 100, 1),
                "ai_risk_label":      engine.categorise_risk(risk_score),
                "demand_level":       str(row.get("demand_level") or "Medium"),
                "median_wage":        mw,
            })

    # ── 6. Emerging careers ───────────────────────────────────────────────────
    emerging = []
    if risk_col in df.columns and "future_proof_score" in df.columns:
        em_df = df[
            (df[risk_col] < 0.4) &
            (df["future_proof_score"] >= df["future_proof_score"].quantile(0.70))
        ]
        if "demand_level" in em_df.columns:
            em_df = em_df[em_df["demand_level"].isin(["High", "Medium"])]

        for _, row in em_df.head(8).iterrows():
            risk_score = _sf(row.get(risk_col), 0.3)
            emerging.append({
                "occupation":    str(row.get("occupation", "")),
                "career_family": str(row.get("career_family", "")),
                "future_proof":  round(_sf(row.get("future_proof_score"), 60.0), 1),
                "ai_risk_label": engine.categorise_risk(risk_score),
                "demand_level":  str(row.get("demand_level") or "High"),
            })

    # ── 7. Summary stats ──────────────────────────────────────────────────────
    summary = {
        "total_occupations":     int(len(df)),
        "total_career_families": int(df["career_family"].nunique())
                                 if "career_family" in df.columns else 0,
        "avg_future_proof":      round(
                                     _sf(df["future_proof_score"].mean(), 50.0), 1
                                 ) if "future_proof_score" in df.columns else 50.0,
        "pct_low_risk":          round(
                                     _sf(
                                         (df[risk_col] < 0.35).sum() / max(len(df), 1) * 100,
                                         0.0
                                     ), 1
                                 ) if risk_col in df.columns else 0.0,
        "high_demand_count":     int((df["demand_level"] == "High").sum())
                                 if "demand_level" in df.columns else 0,
    }

    response = {
        "summary":          summary,
        "sector_risk":      sector_risk,
        "demand_dist":      demand_dist,
        "risk_dist":        risk_dist,
        "scatter_data":     scatter_data,
        "top_careers":      top_careers,
        "emerging_careers": emerging,
        "filters_applied":  {
            "user_type":     user_type,
            "track":         track,
            "pathway":       pathway,
            "career_family": career_family,
        },
    }

    # Final safety net — catches any NaN/Inf that slipped past _sf() calls
    return _sanitise_dict(response)


@router.get(
    "/sectors",
    summary="Sector-level Risk & Demand Summary",
)
async def sector_summary(_=Depends(_require_engine)):
    """Lightweight sector summary — used for the dashboard sidebar."""
    if engine.master is None:
        raise HTTPException(503)

    df = engine.master.copy()
    risk_col = "blended_risk" if "blended_risk" in df.columns else "automation_risk"

    sectors = []
    if "career_family" in df.columns:
        for family, group in df.groupby("career_family"):
            avg_risk = _sf(
                group[risk_col].mean() if risk_col in group.columns else 0.45,
                default=0.45
            )
            sectors.append({
                "name":       str(family),
                "avg_risk":   round(avg_risk * 100, 1),
                "risk_label": engine.categorise_risk(avg_risk),
                "risk_color": engine.RISK_COLORS.get(
                                  engine.categorise_risk(avg_risk), "#95a5a6"
                              ),
                "count":      int(len(group)),
            })

    return _sanitise_dict({"sectors": sorted(sectors, key=lambda x: x["avg_risk"])})
