"""
CareerIntelligenceEngine
========================
Singleton that loads all trained artifacts from Notebooks 02–07
and exposes the full recommendation pipeline as a single Python object.

Load order mirrors the notebook dependency chain:
  02 → master + courses
  03 → retriever + ranker + scaler
  04 → gap engine artifacts
  05 → risk engine artifacts
  06 → course recommender
  07 → integration (this class)
"""
from __future__ import annotations

import json
import os
import time
import warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")


class CareerIntelligenceEngine:
    """Singleton ML engine for the Career & Skills Recommendation System."""

    def __init__(self):
        self.is_loaded: bool = False
        self.semantic_available: bool = False
        self.occupation_count: int = 0
        self.course_count: int = 0

        # Data
        self.master: pd.DataFrame | None = None
        self.courses: pd.DataFrame | None = None

        # Models
        self._retriever = None
        self._ranker = None
        self._scaler = None
        self._st_model = None
        self._skill_dim_vecs: np.ndarray | None = None

        # Config artifacts
        self.SKILL_COLS: list[str] = []
        self.CANONICAL_SKILLS: dict = {}
        self.SKILL_SYNONYM_MAP: dict = {}
        self.CBC_SUBJECT_SKILLS: dict = {}
        self.KCSE_SUBJECT_SKILLS: dict = {}
        self.USER_TYPE_JOB_ZONES: dict = {}
        self.CAREER_GOAL_BOOSTS: dict = {}
        self.SOC_FAMILY_MAP: dict = {}
        self.RISK_THRESHOLDS: dict = {}
        self.RISK_COLORS: dict = {}
        self.RISK_EXPLANATIONS: dict = {}
        self.EDUCATION_COURSE_LEVELS: dict = {}

        # Course TFIDF
        self._course_tfidf = None
        self._course_matrix = None

    # ────────────────────────────────────────────────────────────────────────
    # LOADING
    # ────────────────────────────────────────────────────────────────────────

    def _download_from_gdrive(self, A: Path, M: Path, P: Path):
        """Download artifacts, models, and processed data from Google Drive."""
        from app.core.config import settings
        try:
            import gdown
        except ImportError:
            print("  ⚠️  gdown not installed — skipping Google Drive download")
            return

        os.makedirs(str(A), exist_ok=True)
        os.makedirs(str(M), exist_ok=True)
        os.makedirs(str(P), exist_ok=True)

        if settings.GDRIVE_ARTIFACTS_ID:
            print("  ⬇️  Downloading artifacts from Google Drive...")
            try:
                gdown.download_folder(
                    id=settings.GDRIVE_ARTIFACTS_ID,
                    output=str(A),
                    quiet=False,
                    use_cookies=False
                )
                print("  ✅  Artifacts downloaded.")
            except Exception as e:
                print(f"  ⚠️  Artifacts download failed: {e}")

        if settings.GDRIVE_MODELS_ID:
            print("  ⬇️  Downloading models from Google Drive...")
            try:
                gdown.download_folder(
                    id=settings.GDRIVE_MODELS_ID,
                    output=str(M),
                    quiet=False,
                    use_cookies=False
                )
                print("  ✅  Models downloaded.")
            except Exception as e:
                print(f"  ⚠️  Models download failed: {e}")

        if settings.GDRIVE_PROCESSED_ID:
            print("  ⬇️  Downloading processed data from Google Drive...")
            try:
                gdown.download_folder(
                    id=settings.GDRIVE_PROCESSED_ID,
                    output=str(P),
                    quiet=False,
                    use_cookies=False
                )
                print("  ✅  Processed data downloaded.")
            except Exception as e:
                print(f"  ⚠️  Processed data download failed: {e}")

    def load(self, artifacts_dir: Path | None = None, model_dir: Path | None = None,
             processed_dir: Path | None = None):
        """Load all ML artifacts. Called once at application startup."""
        from app.core.config import settings

        A = artifacts_dir or settings.ARTIFACTS_DIR
        M = model_dir or settings.MODEL_DIR
        P = processed_dir or settings.PROCESSED_DIR

        # ── Download from Google Drive before loading ─────────────────────
        self._download_from_gdrive(A, M, P)

        self._load_data(P)
        self._load_models(M)
        self._load_artifacts(A, M)
        self._load_semantic_model(M, settings.SENTENCE_TRANSFORMER_MODEL)

        self.is_loaded = True
        print(f"  ✅  Engine loaded | {self.occupation_count} occupations | "
              f"{self.course_count} courses | semantic={self.semantic_available}")

    def _load_data(self, P: Path):
        try:
            self.master = pd.read_parquet(P / "master_occupation_profiles.parquet")
            self.occupation_count = len(self.master)
            print(f"     Master profiles : {self.master.shape}")
        except FileNotFoundError:
            print(f"  ⚠️  master_occupation_profiles.parquet not found at {P}")
            self.master = self._build_demo_master()
            self.occupation_count = len(self.master)

        try:
            self.courses = pd.read_parquet(P / "unified_courses.parquet")
            self.course_count = len(self.courses)
            print(f"     Course catalogue: {self.courses.shape}")
        except FileNotFoundError:
            print(f"  ⚠️  unified_courses.parquet not found at {P}")
            self.courses = self._build_demo_courses()
            self.course_count = len(self.courses)

    def _load_models(self, M: Path):
        for name, attr, fname in [
            ("career_retriever", "_retriever", "career_retriever.pkl"),
            ("career_ranker",    "_ranker",    "career_ranker_gbm.pkl"),
            ("skill_scaler",     "_scaler",    "skill_scaler.pkl"),
        ]:
            try:
                setattr(self, attr, joblib.load(M / fname))
                print(f"     {name} : loaded")
            except FileNotFoundError:
                print(f"  ⚠️  {fname} not found — will use fallback")

        # Gap engine bundle
        try:
            gap = joblib.load(M / "skills_gap_engine.pkl")
            self.SKILL_COLS = gap.get("skill_cols", [])
            self.CANONICAL_SKILLS = gap.get("canonical_skills", {})
            print(f"     Gap engine : loaded ({len(self.SKILL_COLS)} skill dims)")
        except FileNotFoundError:
            self.SKILL_COLS = self._derive_skill_cols()
            print(f"  ⚠️  skills_gap_engine.pkl not found — derived {len(self.SKILL_COLS)} skill cols")

        # Risk engine bundle
        try:
            risk = joblib.load(M / "ai_risk_engine.pkl")
            self.RISK_THRESHOLDS = risk.get("risk_thresholds", {})
            self.RISK_COLORS = risk.get("risk_colors", {})
            self.RISK_EXPLANATIONS = risk.get("risk_explanations", {})
            print("     Risk engine : loaded")
        except FileNotFoundError:
            self._set_default_risk_config()
            print("  ⚠️  ai_risk_engine.pkl not found — using defaults")

        # Course recommender bundle
        try:
            course_rec = joblib.load(M / "course_recommender_v2.pkl")
            self._course_tfidf = course_rec["tfidf_vectorizer"]
            self._course_matrix = course_rec["course_matrix"]
            self.EDUCATION_COURSE_LEVELS = course_rec.get("education_level_map", {})
            print("     Course recommender : loaded")
        except FileNotFoundError:
            self._build_course_tfidf()
            self._set_default_edu_levels()
            print("  ⚠️  course_recommender_v2.pkl not found — built from catalogue")

    def _load_artifacts(self, A: Path, M: Path):
        json_artifacts = {
            "SKILL_SYNONYM_MAP":    "skill_synonym_map.json",
            "CBC_SUBJECT_SKILLS":   "cbc_subject_skills.json",
            "KCSE_SUBJECT_SKILLS":  "kcse_subject_skills.json",
            "USER_TYPE_JOB_ZONES":  "user_type_job_zones.json",
            "CAREER_GOAL_BOOSTS":   "career_goal_boosts.json",
            "SOC_FAMILY_MAP":       "soc_family_map.json",
        }
        for attr, fname in json_artifacts.items():
            try:
                with open(A / fname) as f:
                    setattr(self, attr, json.load(f))
                print(f"     {fname} : loaded")
            except FileNotFoundError:
                print(f"  ⚠️  {fname} not found")

        # Skill dim vectors
        try:
            self._skill_dim_vecs = joblib.load(M / "skill_dim_vectors.pkl")
            print(f"     Skill dim vectors : {self._skill_dim_vecs.shape}")
        except FileNotFoundError:
            print("  ⚠️  skill_dim_vectors.pkl not found")

    def _load_semantic_model(self, M: Path, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(model_name)
            self.semantic_available = True
            print(f"     SentenceTransformer({model_name}) : loaded")
        except ImportError:
            print("  ⚠️  sentence-transformers not installed — using TF-IDF fallback")

    # ────────────────────────────────────────────────────────────────────────
    # FALLBACK BUILDERS (when artifacts missing — useful in CI/test)
    # ────────────────────────────────────────────────────────────────────────

    def _derive_skill_cols(self) -> list[str]:
        if self.master is None:
            return []
        exclude = {"o*net-soc_code", "occupation", "title", "description",
                   "career_family", "job_zone", "min_education", "automation_risk",
                   "ai_replacement_risk", "composite_demand", "demand_level",
                   "median_wage_2022", "employment_2022", "employment_2032",
                   "employment_change_pct", "blended_risk", "risk_category",
                   "future_proof_score", "skill_based_risk"}
        return [c for c in self.master.columns
                if c not in exclude and self.master[c].dtype in ["float64", "float32", "int64"]]

    def _build_course_tfidf(self):
        if self.courses is None or self.courses.empty:
            return
        from sklearn.feature_extraction.text import TfidfVectorizer

        def _text(row):
            parts = [str(row.get("course_title", "")) * 3,
                     str(row.get("skills_covered", "")),
                     str(row.get("subject", ""))]
            return " ".join(filter(None, parts)).lower()

        texts = self.courses.apply(_text, axis=1)
        self._course_tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=15000,
                                              min_df=1, sublinear_tf=True)
        self._course_matrix = self._course_tfidf.fit_transform(texts)

    def _set_default_risk_config(self):
        self.RISK_THRESHOLDS = {
            "Low":       (0.00, 0.35),
            "Medium":    (0.35, 0.55),
            "High":      (0.55, 0.72),
            "Very High": (0.72, 1.00),
        }
        self.RISK_COLORS = {
            "Low": "#27ae60", "Medium": "#f39c12",
            "High": "#e67e22", "Very High": "#e74c3c",
        }
        self.RISK_EXPLANATIONS = {
            "Low": "This career has LOW AI replacement risk. It relies on human judgment, "
                   "creativity, and social intelligence — areas where AI remains weak.",
            "Medium": "This career has MEDIUM AI replacement risk. Some tasks may be automated "
                      "but the role requires human oversight, creativity, and interpersonal skills.",
            "High": "This career has HIGH AI replacement risk. Many routine tasks are likely to be "
                    "automated. Upskilling towards creativity, leadership, and complex problem-solving "
                    "is strongly recommended.",
            "Very High": "This career has VERY HIGH AI replacement risk. Plan a skills transition "
                         "towards a lower-risk role or develop AI oversight competencies.",
        }

    def _set_default_edu_levels(self):
        self.EDUCATION_COURSE_LEVELS = {
            "cbc":          ["Foundation"],
            "8-4-4":        ["Foundation", "Intermediate"],
            "diploma":      ["Foundation", "Intermediate"],
            "graduate":     ["Intermediate", "Advanced"],
            "postgraduate": ["Advanced"],
            "professional": ["Intermediate", "Advanced"],
        }

    def _build_demo_master(self) -> pd.DataFrame:
        """Return a tiny demo dataset so the API starts without real data."""
        rows = [
            {"onet_code": "15-1252.00", "occupation": "Software Developers",
             "career_family": "Technology", "job_zone": 4, "min_education": "Bachelors",
             "automation_risk": 0.2, "blended_risk": 0.22, "future_proof_score": 82,
             "demand_level": "High", "median_wage_2022": 120730,
             "employment_change_pct": 25.0, "composite_demand": 0.9},
            {"onet_code": "15-1211.00", "occupation": "Computer Systems Analysts",
             "career_family": "Technology", "job_zone": 4, "min_education": "Bachelors",
             "automation_risk": 0.35, "blended_risk": 0.38, "future_proof_score": 70,
             "demand_level": "Medium", "median_wage_2022": 99270,
             "employment_change_pct": 9.0, "composite_demand": 0.65},
            {"onet_code": "29-1141.00", "occupation": "Registered Nurses",
             "career_family": "Healthcare", "job_zone": 4, "min_education": "Bachelors",
             "automation_risk": 0.1, "blended_risk": 0.12, "future_proof_score": 88,
             "demand_level": "High", "median_wage_2022": 81220,
             "employment_change_pct": 6.0, "composite_demand": 0.85},
        ]
        return pd.DataFrame(rows)

    def _build_demo_courses(self) -> pd.DataFrame:
        rows = [
            {"course_title": "Python for Data Science", "platform": "Coursera",
             "subject": "programming", "skills_covered": "python programming data analysis",
             "std_level": "Foundation", "quality_score": 0.9, "is_free": False,
             "duration_hours": 30, "url": "https://coursera.org"},
            {"course_title": "Machine Learning Specialisation", "platform": "Coursera",
             "subject": "machine learning", "skills_covered": "ml deep learning neural networks",
             "std_level": "Intermediate", "quality_score": 0.95, "is_free": False,
             "duration_hours": 60, "url": "https://coursera.org"},
        ]
        return pd.DataFrame(rows)

    # ────────────────────────────────────────────────────────────────────────
    # CORE PIPELINE METHODS
    # ────────────────────────────────────────────────────────────────────────

    def normalise_skill(self, skill: str) -> str:
        return self.SKILL_SYNONYM_MAP.get(skill.lower().strip(), skill.lower().strip())

    def categorise_risk(self, score: float) -> str:
        for label, (lo, hi) in self.RISK_THRESHOLDS.items():
            if lo <= score < hi:
                return label
        return "Very High"

    def parse_user_skills(self, raw_input: dict) -> dict[str, float]:
        """Convert raw user input into O*NET skill dimension scores [0-7]."""
        skills_raw = raw_input.get("skills", "")
        soft_raw   = raw_input.get("soft_skills", "")
        user_type  = raw_input.get("user_type", "graduate").lower()

        explicit = [self.normalise_skill(s) for s in skills_raw.split(",") if s.strip()]
        explicit += [self.normalise_skill(s) for s in soft_raw.split(",") if s.strip()]

        if user_type == "cbc":
            pathway = raw_input.get("pathway", "")
            explicit += [self.normalise_skill(s)
                         for s in self.CBC_SUBJECT_SKILLS.get(pathway, [])]
        elif user_type == "8-4-4":
            for subj in raw_input.get("subject_combination", "").split(","):
                explicit += [self.normalise_skill(s)
                              for s in self.KCSE_SUBJECT_SKILLS.get(subj.strip(), [])]

        dim_scores = {col: 0.0 for col in self.SKILL_COLS}
        if not self.SKILL_COLS:
            return dim_scores

        if (self.semantic_available and self._skill_dim_vecs is not None
                and self._st_model is not None and explicit):
            user_vecs  = self._st_model.encode(explicit, show_progress_bar=False)
            sim_matrix = cosine_similarity(user_vecs, self._skill_dim_vecs)
            for i in range(len(explicit)):
                top3 = np.argsort(sim_matrix[i])[::-1][:3]
                for rank, dim_idx in enumerate(top3):
                    col    = self.SKILL_COLS[dim_idx]
                    score  = float(sim_matrix[i][dim_idx])
                    weight = 1.0 if rank == 0 else (0.6 if rank == 1 else 0.3)
                    dim_scores[col] = min(7.0, dim_scores[col] + score * weight * 7.0)
        else:
            for skill in explicit:
                for col, desc in self.CANONICAL_SKILLS.items():
                    if col in dim_scores and (
                        skill in desc or any(w in desc for w in skill.split())
                    ):
                        dim_scores[col] = min(7.0, dim_scores.get(col, 0.0) + 2.5)

        return dim_scores

    def recommend_careers(self, raw_input: dict, n: int = 5) -> pd.DataFrame:
        """Return top-N career recommendations for a user profile."""
        user_skill_scores = self.parse_user_skills(raw_input)
        user_type         = raw_input.get("user_type", "graduate").lower()
        career_goals      = raw_input.get("career_goals", "").lower()

        allowed_zones = self.USER_TYPE_JOB_ZONES.get(user_type, [1, 2, 3, 4, 5])
        df = self.master.copy()
        if "job_zone" in df.columns and allowed_zones:
            df = df[df["job_zone"].isin(allowed_zones)]
        if df.empty:
            df = self.master.copy()

        if not self.SKILL_COLS:
            top = df.sort_values("future_proof_score", ascending=False).head(n)
            return self._format_recommendations(top, {})

        skill_matrix = df[self.SKILL_COLS].fillna(0).values
        user_vec     = np.array([user_skill_scores.get(c, 0.0) for c in self.SKILL_COLS])

        if user_vec.sum() == 0:
            top = df.sort_values("future_proof_score", ascending=False).head(n)
            return self._format_recommendations(top, user_skill_scores)

        sims = cosine_similarity([user_vec], skill_matrix)[0]
        df = df.copy()
        df["_cosine_sim"] = sims

        boosts = self.CAREER_GOAL_BOOSTS.get("keywords", {})
        def goal_boost(row):
            bonus = 0.0
            for keyword, families in boosts.items():
                if keyword in career_goals:
                    if row.get("career_family", "") in families:
                        bonus += 0.05
            return bonus

        if career_goals and boosts:
            df["_goal_boost"] = df.apply(goal_boost, axis=1)
            df["_score"] = df["_cosine_sim"] + df["_goal_boost"]
        else:
            df["_score"] = df["_cosine_sim"]

        if self._ranker is not None and self._scaler is not None:
            try:
                feats = df[self.SKILL_COLS].fillna(0).values
                feats_scaled = self._scaler.transform(feats)
                ranker_scores = self._ranker.predict_proba(feats_scaled)[:, 1]
                df["_score"] = 0.6 * df["_score"] + 0.4 * ranker_scores
            except Exception:
                pass

        top = df.nlargest(n, "_score")
        return self._format_recommendations(top, user_skill_scores)

    def _safe_float(self, val, default=0.0) -> float:
        try:
            v = float(val)
            if np.isnan(v) or np.isinf(v):
                return default
            return v
        except (TypeError, ValueError):
            return default

    def _get_demand(self, row) -> str:
        for col in ["demand_level", "demand", "growth_category", "bls_demand_level"]:
            val = row.get(col, None)
            if val and str(val).lower() not in ("nan", "none", "unknown", ""):
                v = str(val).strip()
                if v in ("High", "Medium", "Low"):
                    return v
                vl = v.lower()
                if "high" in vl or "fast" in vl or "much faster" in vl:
                    return "High"
                if "low" in vl or "slow" in vl or "decline" in vl or "little" in vl:
                    return "Low"
                if "medium" in vl or "average" in vl or "moderate" in vl:
                    return "Medium"
        return "Medium"

    def _format_recommendations(self, df: pd.DataFrame,
                                  user_skill_scores: dict) -> pd.DataFrame:
        scores = df.get("_score", pd.Series(dtype=float))
        if len(scores) > 0:
            s_min = self._safe_float(scores.min(), 0.0)
            s_max = self._safe_float(scores.max(), 1.0)
            score_range = s_max - s_min if s_max > s_min else 1.0
        else:
            s_min, score_range = 0.0, 1.0

        rows = []
        for rank, (_, row) in enumerate(df.iterrows(), start=1):
            raw_score = self._safe_float(row.get("_score", 0.5), 0.5)

            if score_range > 0:
                normalised = (raw_score - s_min) / score_range
                match_pct  = round(55 + normalised * 43, 1)
            else:
                match_pct = 70.0

            risk_val = self._safe_float(
                row.get("blended_risk", row.get("automation_risk", 0.45)), 0.45)

            rows.append({
                "Rank":               rank,
                "Career":             str(row.get("occupation", "Unknown")),
                "Career Family":      str(row.get("career_family", "Unknown")),
                "Match Score (%)":    match_pct,
                "Demand Level":       self._get_demand(row),
                "Future Proof Score": self._safe_float(row.get("future_proof_score", 50), 50),
                "Median Wage (USD)":  self._safe_float(row.get("median_wage_2022", 0), 0),
                "Min Education":      str(row.get("min_education", "Unknown")),
                "AI Risk":            self.categorise_risk(risk_val),
                "_onet_code":         str(row.get("onet_code", "")),
            })
        return pd.DataFrame(rows)

    def analyse_skills_gap(self, user_skill_scores: dict,
                            occupation_row: pd.Series,
                            top_n_gaps: int = 8,
                            top_n_strong: int = 5) -> dict:
        occ_name  = occupation_row.get("occupation", "Unknown")

        raw_scores = []
        for c in self.SKILL_COLS:
            try:
                v = float(occupation_row.get(c, 0) or 0)
                raw_scores.append(v if np.isfinite(v) else 0.0)
            except (TypeError, ValueError):
                raw_scores.append(0.0)
        imp_total = sum(raw_scores) or 1.0

        importance = {}
        for col, raw in zip(self.SKILL_COLS, raw_scores):
            imp = raw / imp_total
            importance[col] = imp if np.isfinite(imp) else 0.0

        gap_details = []
        for col in self.SKILL_COLS:
            try:
                required = float(occupation_row.get(col, 0) or 0)
                required = required if np.isfinite(required) else 0.0
            except (TypeError, ValueError):
                required = 0.0
            current = self._safe_float(user_skill_scores.get(col, 0))
            gap     = max(0.0, required - current)
            imp     = importance.get(col, 0.0)
            w_gap   = gap * imp
            gap_details.append({
                "dimension":    col.replace("skill_", "").replace("_", " ").title(),
                "col":          col,
                "required":     round(required, 2),
                "current":      round(current, 2),
                "gap":          round(gap, 2),
                "importance":   round(imp, 4),
                "weighted_gap": round(w_gap, 4),
            })

        gap_details.sort(key=lambda x: x["weighted_gap"], reverse=True)

        top_gaps    = [g for g in gap_details if g["gap"] > 0][:top_n_gaps]
        top_strong  = sorted(
            [g for g in gap_details if g["current"] >= g["required"] and g["required"] > 0],
            key=lambda x: x["current"], reverse=True
        )[:top_n_strong]

        max_gap    = sum(r * importance.get(c, 0.0)
                         for c, r in zip(self.SKILL_COLS, raw_scores))
        actual_gap = sum(g["weighted_gap"] for g in gap_details)
        alignment  = round((1 - actual_gap / max(max_gap, 1e-6)) * 100, 1)
        if not np.isfinite(alignment):
            alignment = 0.0

        return {
            "occupation":    occ_name,
            "alignment_pct": max(0.0, min(100.0, alignment)),
            "top_gaps":      top_gaps,
            "top_strengths": top_strong,
            "total_dims":    len(self.SKILL_COLS),
        }

    def search_courses_for_skill(self, skill_name: str, top_k: int = 3,
                                  level_filter: str | None = None,
                                  min_quality: float = 0.3) -> list[dict]:
        if self._course_tfidf is None or self._course_matrix is None or self.courses is None:
            return []

        query     = skill_name.lower().replace("_", " ")
        query_vec = self._course_tfidf.transform([query])
        sims      = cosine_similarity(query_vec, self._course_matrix)[0]

        mask = self.courses.get("quality_score", pd.Series(np.ones(len(self.courses)))).fillna(0) >= min_quality
        if level_filter:
            std_col = "std_level" if "std_level" in self.courses.columns else "level"
            mask = mask & (self.courses[std_col].fillna("") == level_filter)

        masked = sims * mask.astype(float)
        top_idx = [i for i in np.argsort(masked)[::-1] if masked[i] > 0.01][:top_k]

        results = []
        for idx in top_idx:
            row = self.courses.iloc[idx]
            results.append({
                "course_title":   str(row.get("course_title", "Unknown")),
                "platform":       str(row.get("platform", "Unknown")),
                "level":          str(row.get("std_level", row.get("level", "Unknown"))),
                "subject":        str(row.get("subject", "")),
                "skills_covered": str(row.get("skills_covered", ""))[:120],
                "quality_score":  round(float(row.get("quality_score", 0) or 0), 2),
                "duration_hours": row.get("duration_hours", None),
                "is_free":        bool(row.get("is_free", False)),
                "url":            str(row.get("url", "")),
                "skill_match_pct": round(float(masked[idx]) * 100, 1),
                "skill_gap":       skill_name.replace("_", " ").title(),
            })
        return results

    def generate_learning_path(self, gap_report: dict, user_type: str = "graduate",
                                courses_per_gap: int = 2) -> dict:
        edu_levels = self.EDUCATION_COURSE_LEVELS.get(user_type.lower(),
                                                        ["Foundation", "Intermediate"])
        top_gaps = gap_report.get("top_gaps", [])
        stages   = []
        total_hrs = 0.0

        for stage_idx, level in enumerate(edu_levels[:3], start=1):
            stage_gaps    = top_gaps[stage_idx - 1::len(edu_levels)] if top_gaps else []
            stage_courses = []
            for gap in stage_gaps[:4]:
                courses = self.search_courses_for_skill(
                    gap["col"], top_k=courses_per_gap, level_filter=level
                )
                if not courses:
                    courses = self.search_courses_for_skill(
                        gap["col"], top_k=courses_per_gap, level_filter=None
                    )
                stage_courses.extend(courses)

            seen_titles   = set()
            unique_courses = []
            for c in stage_courses:
                if c["course_title"] not in seen_titles:
                    seen_titles.add(c["course_title"])
                    unique_courses.append(c)

            hrs = sum(float(c.get("duration_hours") or 20) for c in unique_courses)
            total_hrs += hrs
            stages.append({
                "stage":     stage_idx,
                "level":     level,
                "title":     f"Stage {stage_idx}: {level}",
                "courses":   unique_courses,
                "hours_est": round(hrs, 0),
            })

        return {
            "stages":      stages,
            "total_hours": round(total_hrs, 0),
            "user_type":   user_type,
        }

    def get_risk_mitigation(self, risk_category: str) -> list[str]:
        advice_map = {
            "Low":       ["Continue building deep expertise — your role is future-proof.",
                          "Embrace AI tools to amplify your productivity.",
                          "Stay current with AI developments in your sector."],
            "Medium":    ["Identify automatable tasks and upskill away from them.",
                          "Develop leadership and creative problem-solving skills.",
                          "Become a skilled human-AI collaborator."],
            "High":      ["Urgently develop management or creative skills.",
                          "Consider adjacent roles with lower AI risk.",
                          "Pursue certifications in higher-complexity areas."],
            "Very High": ["Plan a skills transition into a lower-risk career.",
                          "Build AI oversight and auditing competencies.",
                          "Consult a career counsellor for a reskilling roadmap."],
        }
        return advice_map.get(risk_category, [])

    def _sanitise(self, obj):
        if isinstance(obj, dict):
            return {k: self._sanitise(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitise(v) for v in obj]
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return 0.0
            return obj
        if isinstance(obj, np.floating):
            v = float(obj)
            return 0.0 if (np.isnan(v) or np.isinf(v)) else v
        if isinstance(obj, np.integer):
            return int(obj)
        return obj

    def run_full_pipeline(self, raw_input: dict, n: int = 5,
                           courses_per_gap: int = 2) -> dict:
        t0 = time.perf_counter()

        recommendations = self.recommend_careers(raw_input, n=n)
        user_skill_scores = self.parse_user_skills(raw_input)

        career_details = []
        for _, rec in recommendations.iterrows():
            career_title = rec["Career"]
            occ = self.master[self.master["occupation"].str.lower() == career_title.lower()]
            if occ.empty:
                occ = self.master[self.master["occupation"].str.contains(
                    career_title.split()[0], case=False, na=False)]
            if occ.empty:
                continue
            occ_row = occ.iloc[0]

            blended_risk  = self._safe_float(
                occ_row.get("blended_risk", occ_row.get("automation_risk", 0.45)), 0.45)
            risk_category = self.categorise_risk(blended_risk)

            gap_report    = self.analyse_skills_gap(user_skill_scores, occ_row)
            learning_path = self.generate_learning_path(
                gap_report, user_type=raw_input.get("user_type", "graduate"),
                courses_per_gap=courses_per_gap)

            career_details.append({
                "rank":         int(rec["Rank"]),
                "career_info":  {
                    "title":          str(career_title),
                    "career_family":  str(rec.get("Career Family", "")),
                    "match_score":    self._safe_float(rec.get("Match Score (%)", 70), 70),
                    "demand_level":   str(rec.get("Demand Level", "Medium")),
                    "median_wage":    self._safe_float(rec.get("Median Wage (USD)", 0), 0),
                    "min_education":  str(rec.get("Min Education", "")),
                    "onet_code":      str(rec.get("_onet_code", "")),
                },
                "risk_profile": {
                    "ai_risk_score":      round(blended_risk * 100, 1),
                    "ai_risk_label":      risk_category,
                    "ai_risk_color":      self.RISK_COLORS.get(risk_category, "#95a5a6"),
                    "future_proof_score": self._safe_float(occ_row.get("future_proof_score", 50), 50),
                    "risk_explanation":   self.RISK_EXPLANATIONS.get(risk_category, ""),
                    "mitigation_advice":  self.get_risk_mitigation(risk_category),
                },
                "gap_report":    gap_report,
                "learning_path": learning_path,
            })

        result = {
            "career_details":  career_details,
            "recommendations": recommendations.drop(columns=["_onet_code"], errors="ignore")
                                              .to_dict(orient="records"),
            "pipeline_ms":     round((time.perf_counter() - t0) * 1000, 1),
            "user_type":       raw_input.get("user_type", "graduate"),
        }
        return self._sanitise(result)


# ── Global singleton ──────────────────────────────────────────────────────────
engine = CareerIntelligenceEngine()

