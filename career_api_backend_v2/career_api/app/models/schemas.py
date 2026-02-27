"""
Pydantic schemas for all API request and response models.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserType(str, Enum):
    cbc          = "cbc"
    eight44      = "8-4-4"
    diploma      = "diploma"
    graduate     = "graduate"
    postgraduate = "postgraduate"
    professional = "professional"


class CourseLevel(str, Enum):
    foundation    = "Foundation"
    intermediate  = "Intermediate"
    advanced      = "Advanced"


class RiskCategory(str, Enum):
    low       = "Low"
    medium    = "Medium"
    high      = "High"
    very_high = "Very High"


# ── Shared nested models ──────────────────────────────────────────────────────

class SkillGap(BaseModel):
    dimension:    str            = Field(..., description="Human-readable O*NET skill dimension")
    col:          str            = Field(..., description="Internal column name")
    required:     float          = Field(..., description="Score required by the occupation (0–7)")
    current:      float          = Field(..., description="User's estimated score (0–7)")
    gap:          float          = Field(..., description="Gap = required - current (0 if positive)")
    importance:   Optional[float] = Field(default=0.0, description="Relative importance weight for this occupation")
    weighted_gap: Optional[float] = Field(default=0.0, description="Gap × importance")


class SkillStrength(BaseModel):
    dimension:    str
    col:          str
    required:     float
    current:      float
    gap:          float
    importance:   Optional[float] = 0.0
    weighted_gap: Optional[float] = 0.0


class GapReport(BaseModel):
    occupation:    str
    alignment_pct: float = Field(..., description="Skill alignment percentage (0–100)")
    top_gaps:      List[SkillGap]
    top_strengths: List[SkillStrength]
    total_dims:    int


class CourseRecommendation(BaseModel):
    course_title:   str
    platform:       str
    level:          str
    subject:        str
    skills_covered: str
    quality_score:  float
    duration_hours: Optional[float] = None
    is_free:        bool
    url:            str
    skill_match_pct: float
    skill_gap:      str


class LearningStage(BaseModel):
    stage:      int
    level:      str
    title:      str
    courses:    List[CourseRecommendation]
    hours_est:  float


class LearningPath(BaseModel):
    stages:      List[LearningStage]
    total_hours: float
    user_type:   str


class RiskProfile(BaseModel):
    ai_risk_score:      float = Field(..., description="AI replacement risk 0–100")
    ai_risk_label:      RiskCategory
    ai_risk_color:      str   = Field(..., description="Hex colour for UI display")
    future_proof_score: float = Field(..., description="Future-proof composite 0–100")
    risk_explanation:   str
    mitigation_advice:  List[str]


class CareerInfo(BaseModel):
    title:          str
    career_family:  str
    match_score:    float = Field(..., description="Cosine similarity match 0–100")
    demand_level:   str
    median_wage:    Optional[float] = None
    min_education:  str
    onet_code:      str


class CareerDetail(BaseModel):
    rank:          int
    career_info:   CareerInfo
    risk_profile:  RiskProfile
    gap_report:    GapReport
    learning_path: LearningPath


class CareerSummary(BaseModel):
    Rank:               int
    Career:             str
    career_family:      Optional[str] = Field(None, alias="Career Family")
    match_score:        Optional[float] = Field(None, alias="Match Score (%)")
    demand_level:       Optional[str]  = Field(None, alias="Demand Level")
    future_proof_score: Optional[float] = Field(None, alias="Future Proof Score")
    median_wage:        Optional[float] = Field(None, alias="Median Wage (USD)")
    min_education:      Optional[str]  = Field(None, alias="Min Education")
    ai_risk:            Optional[str]  = Field(None, alias="AI Risk")

    model_config = {"populate_by_name": True}


# ── Request models ────────────────────────────────────────────────────────────

class UserProfileRequest(BaseModel):
    """
    Universal user profile for career recommendation.
    Supports all Kenyan education levels: CBC, 8-4-4, TVET, University.
    """
    user_type: UserType = Field(
        default=UserType.graduate,
        description="Education level / user category"
    )
    skills: str = Field(
        default="",
        description="Comma-separated list of technical skills (e.g. 'python, sql, data analysis')"
    )
    soft_skills: str = Field(
        default="",
        description="Comma-separated soft skills (e.g. 'communication, leadership, teamwork')"
    )
    career_goals: str = Field(
        default="",
        description="Free-text description of career aspirations"
    )
    interests: str = Field(
        default="",
        description="Areas of personal interest"
    )

    # CBC-specific
    pathway: Optional[str] = Field(None, description="CBC pathway (e.g. 'Arts and Sports Science')")
    track:   Optional[str] = Field(None, description="CBC track")

    # 8-4-4-specific
    subject_combination: Optional[str] = Field(
        None, description="KCSE subject combination (comma-separated)"
    )

    # Graduate-specific
    degree_programme: Optional[str] = Field(None, description="University degree programme")

    # Professional-specific
    industry: Optional[str] = Field(None, description="Current industry")
    major:    Optional[str] = Field(None, description="Area of specialisation")

    @field_validator("skills", "soft_skills", "career_goals", mode="before")
    @classmethod
    def clean_string(cls, v):
        return str(v).strip() if v else ""


class RecommendRequest(UserProfileRequest):
    n_recommendations: int = Field(
        default=5, ge=1, le=20,
        description="Number of career recommendations to return"
    )
    courses_per_gap: int = Field(
        default=2, ge=1, le=5,
        description="Max courses to recommend per skill gap"
    )
    include_learning_path: bool = Field(
        default=True, description="Include learning path in response"
    )


class SkillsGapRequest(BaseModel):
    user_skills: str = Field(
        ..., description="Comma-separated skills (technical and soft)"
    )
    occupation:  str = Field(
        ..., description="Target occupation name (e.g. 'Software Developers')"
    )
    user_type:   UserType = Field(default=UserType.graduate)
    top_n_gaps:  int = Field(default=8, ge=1, le=20)
    top_n_strong: int = Field(default=5, ge=1, le=10)


class CourseSearchRequest(BaseModel):
    skill_name:   str = Field(..., description="Skill or topic to find courses for")
    top_k:        int = Field(default=5, ge=1, le=20)
    level_filter: Optional[CourseLevel] = None
    min_quality:  float = Field(default=0.3, ge=0.0, le=1.0)


class RiskRequest(BaseModel):
    occupation: str = Field(..., description="Occupation name to score")


# ── Response models ───────────────────────────────────────────────────────────

class RecommendResponse(BaseModel):
    recommendations:  List[dict]  # summary table
    career_details:   List[CareerDetail]
    pipeline_ms:      float
    user_type:        str
    meta: dict = Field(default_factory=dict)


class SkillsGapResponse(BaseModel):
    gap_report:    GapReport
    learning_path: Optional[LearningPath] = None
    pipeline_ms:   float


class CourseSearchResponse(BaseModel):
    courses:      List[CourseRecommendation]
    query:        str
    total_found:  int


class RiskResponse(BaseModel):
    occupation:         str
    ai_risk_score:      float
    ai_risk_label:      str
    future_proof_score: float
    risk_explanation:   str
    mitigation_advice:  List[str]


class OccupationListResponse(BaseModel):
    occupations:  List[str]
    total:        int
    career_families: dict


class HealthResponse(BaseModel):
    status:  str
    engine:  dict
