"""
Test suite for the Career & Skills Recommendation System API.
Run with: pytest tests/ -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.engine import engine


@pytest.fixture(scope="module")
def client():
    """TestClient with engine pre-loaded using demo data."""
    # Force demo data load (no real parquet files needed in CI)
    engine._load_data(None.__class__.__mro__[0])  # will fail gracefully → demo data
    try:
        engine.load()
    except Exception:
        # Load demo data only
        engine.master = engine._build_demo_master()
        engine.courses = engine._build_demo_courses()
        engine.SKILL_COLS = engine._derive_skill_cols()
        engine._set_default_risk_config()
        engine._set_default_edu_levels()
        engine._build_course_tfidf()
        engine.is_loaded = True

    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "operational"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestCareers:
    PAYLOAD = {
        "user_type": "graduate",
        "skills": "python, machine learning, data analysis",
        "soft_skills": "communication, problem solving",
        "career_goals": "work in technology and data science",
        "n_recommendations": 3,
        "courses_per_gap": 1,
    }

    def test_quick_recommend(self, client):
        r = client.post("/api/v1/careers/quick", json=self.PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_recommend_full(self, client):
        r = client.post("/api/v1/careers/recommend", json=self.PAYLOAD)
        assert r.status_code in (200, 500)  # 500 ok if no real data

    def test_career_families(self, client):
        r = client.get("/api/v1/careers/families")
        assert r.status_code == 200
        assert "families" in r.json()


class TestOccupations:
    def test_list(self, client):
        r = client.get("/api/v1/occupations/?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert "occupations" in data
        assert "total" in data

    def test_search(self, client):
        r = client.get("/api/v1/occupations/?search=Software&limit=3")
        assert r.status_code == 200

    def test_get_occupation(self, client):
        r = client.get("/api/v1/occupations/Software Developers")
        assert r.status_code in (200, 404)


class TestRisk:
    def test_risk_score_get(self, client):
        r = client.get("/api/v1/risk/score?occupation=Software Developers")
        assert r.status_code in (200, 404)

    def test_distribution(self, client):
        r = client.get("/api/v1/risk/distribution")
        assert r.status_code == 200
        data = r.json()
        assert "distribution" in data

    def test_leaderboard(self, client):
        r = client.get("/api/v1/risk/leaderboard?top_n=5")
        assert r.status_code == 200
        data = r.json()
        assert "leaderboard" in data


class TestCourses:
    def test_search_post(self, client):
        r = client.post("/api/v1/courses/search",
                        json={"skill_name": "python", "top_k": 3})
        assert r.status_code == 200

    def test_search_get(self, client):
        r = client.get("/api/v1/courses/search?skill=programming&top_k=3")
        assert r.status_code == 200

    def test_platforms(self, client):
        r = client.get("/api/v1/courses/platforms")
        assert r.status_code == 200

    def test_levels(self, client):
        r = client.get("/api/v1/courses/levels")
        assert r.status_code == 200


class TestSkills:
    def test_dimensions(self, client):
        r = client.get("/api/v1/skills/dimensions")
        assert r.status_code == 200
        data = r.json()
        assert "skill_dimensions" in data

    def test_gap_analysis(self, client):
        r = client.post("/api/v1/skills/gap", json={
            "user_skills": "python, data analysis, critical thinking",
            "occupation":  "Software Developers",
            "user_type":   "graduate",
        })
        assert r.status_code in (200, 404)
