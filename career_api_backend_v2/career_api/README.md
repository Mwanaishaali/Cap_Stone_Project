# 🚀 Career & Skills Recommendation System — FastAPI Backend

Production-ready REST API wrapping your 7-notebook ML pipeline into a clean, documented, deployable service.

---

## Project Structure

```
career_api/
├── app/
│   ├── main.py                     # FastAPI app factory + lifespan
│   ├── core/
│   │   ├── config.py               # Pydantic settings (env vars)
│   │   └── engine.py               # CareerIntelligenceEngine singleton
│   ├── models/
│   │   └── schemas.py              # All Pydantic request/response models
│   └── api/v1/
│       ├── router.py               # Assembles all endpoint routers
│       └── endpoints/
│           ├── careers.py          # /careers — recommendation pipeline
│           ├── skills.py           # /skills  — gap analysis
│           ├── courses.py          # /courses — course search
│           ├── risk.py             # /risk    — AI risk scoring
│           └── occupations.py      # /occupations — catalogue browse
├── tests/
│   └── test_api.py                 # Pytest test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Notebook → API Mapping

| Notebook | What it built | API endpoint |
|----------|--------------|--------------|
| 02 Data Preparation | `master_occupation_profiles.parquet`, `unified_courses.parquet` | All endpoints (data source) |
| 03 Career Recommendation | `career_retriever.pkl`, `career_ranker_gbm.pkl`, `skill_scaler.pkl` | `POST /api/v1/careers/recommend` |
| 04 Skills Gap Engine | `skills_gap_engine.pkl`, `skill_dim_vectors.pkl` | `POST /api/v1/skills/gap` |
| 05 AI Risk Scoring | `ai_risk_engine.pkl` | `GET /api/v1/risk/score`, `/risk/leaderboard` |
| 06 Course Recommender | `course_recommender_v2.pkl` | `POST /api/v1/courses/search` |
| 07 System Integration | Full pipeline | `POST /api/v1/careers/recommend` (all-in-one) |

---

## Quick Start

### 1. Install dependencies
```bash
cd career_api
pip install -r requirements.txt
```

### 2. Set environment variables
```bash
cp .env.example .env
# Edit .env to point to your artifacts, DATA/processed, and models folders
```

### 3. Run the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the interactive docs
- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc

---

## Docker

```bash
# From inside career_api/
docker-compose up --build
```
The compose file mounts `../artifacts`, `../DATA/processed`, and `../models` from your capstone root into the container as read-only volumes.

---

## API Reference

### `POST /api/v1/careers/recommend`
Full pipeline: career matching + skills gap + AI risk + learning path.

```json
{
  "user_type": "graduate",
  "skills": "python, machine learning, sql",
  "soft_skills": "communication, leadership",
  "career_goals": "work in data science and AI",
  "degree_programme": "BSc Computer Science",
  "n_recommendations": 5,
  "courses_per_gap": 2
}
```

**CBC student example:**
```json
{
  "user_type": "cbc",
  "pathway": "Arts and Sports Science",
  "skills": "drawing, design",
  "career_goals": "creative industries",
  "n_recommendations": 5
}
```

**8-4-4 student example:**
```json
{
  "user_type": "8-4-4",
  "subject_combination": "Mathematics, Physics, Chemistry",
  "skills": "problem solving",
  "n_recommendations": 5
}
```

---

### `POST /api/v1/careers/quick`
Fast summary table only (no gap analysis).

---

### `POST /api/v1/skills/gap`
Skills gap analysis for a specific occupation.

```json
{
  "user_skills": "python, data analysis, critical thinking",
  "occupation": "Software Developers",
  "user_type": "graduate",
  "top_n_gaps": 8
}
```

---

### `POST /api/v1/courses/search`
Find courses for a specific skill.

```json
{
  "skill_name": "machine learning",
  "top_k": 5,
  "level_filter": "Intermediate",
  "min_quality": 0.5
}
```

---

### `GET /api/v1/risk/score?occupation=Software+Developers`
AI risk score for any occupation.

---

### `GET /api/v1/risk/leaderboard?top_n=20`
Top future-proof careers ranked by composite score.

---

### `GET /api/v1/occupations/?search=data&career_family=Technology`
Browse/filter occupations catalogue.

---

## Response Structure — `/careers/recommend`

```json
{
  "recommendations": [
    { "Rank": 1, "Career": "Software Developers", "Match Score (%)": 87.3, ... }
  ],
  "career_details": [
    {
      "rank": 1,
      "career_info": { "title": "...", "career_family": "Technology", ... },
      "risk_profile": {
        "ai_risk_score": 22.0,
        "ai_risk_label": "Low",
        "future_proof_score": 82.5,
        "risk_explanation": "...",
        "mitigation_advice": [...]
      },
      "gap_report": {
        "occupation": "Software Developers",
        "alignment_pct": 74.2,
        "top_gaps": [
          { "dimension": "Programming", "required": 6.5, "current": 4.2, "gap": 2.3, ... }
        ],
        "top_strengths": [...]
      },
      "learning_path": {
        "stages": [
          {
            "stage": 1,
            "level": "Intermediate",
            "courses": [
              { "course_title": "...", "platform": "Coursera", "url": "...", ... }
            ]
          }
        ],
        "total_hours": 120
      }
    }
  ],
  "pipeline_ms": 340.2,
  "user_type": "graduate"
}
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTIFACTS_DIR` | `../artifacts` | Path to your capstone `artifacts/` folder |
| `PROCESSED_DIR` | `../DATA/processed` | Path to processed parquet files |
| `MODEL_DIR` | `../models` | Path to trained model `.pkl` files |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |
| `SENTENCE_TRANSFORMER_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model name |
| `DEFAULT_RECOMMENDATIONS` | `5` | Default number of recommendations |

---

## Graceful Degradation

The engine is designed to start even when artifacts are missing:
- **Missing parquet files** → built-in demo dataset (3 occupations)
- **Missing `.pkl` models** → cosine similarity fallback (no ranker re-scoring)
- **sentence-transformers not installed** → TF-IDF keyword matching fallback
- **Missing JSON artifacts** → empty dicts (no goal boosting or CBC skill injection)

This means `uvicorn` will always start successfully. You'll see `⚠️` warnings in the console for missing files.
