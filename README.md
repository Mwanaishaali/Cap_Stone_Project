# Career & Skills Intelligence System
https://careeriq-g4.netlify.app/-visit this link to access the recommendation system

> An AI-powered career recommendation platform that helps Kenyan learners and professionals discover their best-fit careers, understand skill gaps, assess automation risk, and receive personalised learning roadmaps.



---

##  Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Datasets](#-datasets)
- [Notebook Pipeline](#-notebook-pipeline)
- [Models & Algorithms](#-models--algorithms)
- [Key Outputs](#-key-outputs)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [Supported User Types](#-supported-user-types)
- [Project Structure](#-project-structure)
- [Key Design Decisions](#-key-design-decisions)
- [Known Limitations](#-known-limitations)
- [Roadmap](#-roadmap)

---

##  Overview

The  Career & Skills Intelligence System bridges the gap between what Kenyan learners study and what the job market demands. It serves students from both the legacy **8-4-4 curriculum** and the new **Competency-Based Curriculum (CBC)**, as well as TVET diploma holders, graduates, and working professionals.

**What the system produces for each user:**

| Output | Description |
|--------|-------------|
|  **Top-5 Career Recommendations** | Personalised matches from 894 O\*NET occupations with alignment scores |
|  **AI Risk Rating** | Automation risk per career — Low / Medium / High / Very High |
|  **Skills Gap Report** | Critical gaps, moderate gaps, and transferable strengths |
|  **Learning Path** | Curated course sequence (Foundation → Intermediate → Advanced) from Coursera, edX, and Udemy |

---

##  System Architecture

```
User Input  (skills + education level + career goal)
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Stage 1 — Career Recommendation Engine  (NB 03)     │
│  Sentence Transformer encoding → NearestNeighbors    │
│  retrieval (top-50) → GradientBoosting ranker (top-5)│
└────────────────────────┬─────────────────────────────┘
                         │  Top-5 career candidates
                         ▼
┌──────────────────────────────────────────────────────┐
│  Stage 2 — AI Risk Scoring Engine  (NB 05)           │
│  Skill-based risk formula + BLS blending             │
│  → Risk category + Future-Proof Score (0–100)        │
└────────────────────────┬─────────────────────────────┘
                         │  Enriched career cards
                         ▼
┌──────────────────────────────────────────────────────┐
│  Stage 3 — Skills Gap Engine  (NB 04)                │
│  Semantic cosine similarity on O*NET skill vectors   │
│  → Critical / Moderate / Strong skill classification │
└────────────────────────┬─────────────────────────────┘
                         │  Per-career gap reports
                         ▼
┌──────────────────────────────────────────────────────┐
│  Stage 4 — Course Recommender  (NB 06)               │
│  TF-IDF gap-driven search over 8,050 courses         │
│  → Learning path per career per gap                  │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
           Complete JSON output with career cards,
           gap reports, learning paths, dashboard data
```

---

##  Datasets

| Dataset | Source | Records | Role |
|---------|--------|---------|------|
| O\*NET Occupation Data | O\*NET / BLS | 1,016 | Career backbone — 894 unique occupations used in modelling |
| O\*NET Skills | O\*NET | 62,580 rows | 35 skill dimensions per occupation; Level (LV) scores 0–6 |
| O\*NET Job Zones | O\*NET | 923 | Education level ↔ occupation mapping (Zones 1–5) |
| O\*NET Education & Training | O\*NET | 37,125 rows | Required education level per occupation |
| BLS Employment Projections | Bureau of Labour Statistics | 102 | Demand level, employment change, automation risk |
| LinkedIn Job Postings | LinkedIn | 119,320 | Real-world job title demand signal |
| edX Courses | edX | 975 | MOOC catalogue |
| Udemy Courses | Udemy | 3,678 | MOOC catalogue — broad coverage, price variety |
| Coursera Courses | Coursera | 3,404 | MOOC catalogue — quality-scored via reviews |
| Coursera Reviews | Coursera | 107,018 | Sentiment data powering course quality scores |
| CBC Pathways | Kenya MoE | 22 pathways | Kenya CBC track → O\*NET job zone + implicit skill mapping |

> All raw files go in `DATA/new/`. Processed outputs are written to `DATA/processed/`.

---

##  Notebook Pipeline

Run notebooks **in order** — each reads from outputs of the previous.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_data_understanding.ipynb` | EDA of all 11 datasets — shapes, distributions, quality checks |
| 02 | `02_data_preparation.ipynb` | Cleaning, feature engineering, master table + course catalogue build |
| 03 | `03_career_recommendation_model_v3.ipynb` | Two-stage semantic retrieval + GBM ranking pipeline |
| 04 | `04_skills_gap_engine.ipynb` | Semantic skills gap analysis + transferable skills detection |
| 05 | `05_ai_risk_scoring.ipynb` | Blended BLS + skill-based automation risk; future-proof score |
| 06 | `06_course_recommender.ipynb` | Gap-driven TF-IDF course search + learning path sequencer |
| 07 | `07_full_system_integration.ipynb` | End-to-end pipeline assembly + production `recommend()` API |

### Artifact Flow

```
DATA/new/  (raw sources)
    │
    ▼  NB 02
    ├── DATA/processed/master_occupation_profiles.parquet   ← 894 × 58 feature matrix
    ├── DATA/processed/unified_courses.parquet              ← 8,050 × 14 course catalogue
    └── DATA/processed/linkedin_demand.parquet
    │
    ▼  NB 03
    ├── models/career_retriever.pkl                         ← NearestNeighbors index
    ├── models/career_ranker.pkl                            ← GradientBoostingClassifier
    └── artifacts/onet_skill_columns.json                  ← 35 skill column names
    │
    ▼  NB 04
    ├── models/skills_gap_engine.pkl
    ├── models/skill_dim_vectors.pkl                        ← (48 × 384) embeddings
    └── artifacts/skill_importance_weights.json
    │
    ▼  NB 05
    ├── models/ai_risk_engine.pkl
    └── DATA/processed/career_risk_profiles.parquet
    │
    ▼  NB 06
    └── models/course_recommender.pkl                       ← TF-IDF, 15K vocabulary
    │
    ▼  NB 07
    └── models/career_system_v1.pkl                         ← Full integrated system
```

---

##  Models & Algorithms

### Stage 1 — Career Recommendation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Semantic encoder | `all-MiniLM-L6-v2` (Sentence Transformers) | 384-dim embeddings; understands Swahili, jargon, and field-specific language |
| Retrieval | `sklearn.neighbors.NearestNeighbors` (cosine) | Fast broad recall — top-50 from 894 occupations |
| Ranking | `sklearn.ensemble.GradientBoostingClassifier` | Learns optimal weights across skill match, demand, risk, zone fit, and keyword signals |
| Skill enrichment | 250+ synonym map + CBC/KCSE implicit boosts | Compensates for limited vocabulary in user free-text |

### Stage 2 — AI Risk Scoring

```
Blended Risk Score = 0.5 × BLS_automation_prob + 0.5 × skill_derived_risk

High-risk skill signals:  Operation & Control, Equipment Maintenance,
                          Operations Monitoring, Quality Control, Mathematics

Low-risk skill signals:   Social Perceptiveness, Judgment & Decision Making,
                          Instructing, Negotiation, Originality, Speaking

Future-Proof Score (0–100) = 40% demand + 40% (1 − risk) + 20% salary
```

### Stage 3 — Skills Gap Engine

- Cosine similarity between user skill vector and O\*NET occupation requirements
- `MinMaxScaler` for score normalisation
- Sentence Transformer embeddings for language-agnostic skill name resolution

### Stage 4 — Course Recommender

- `TfidfVectorizer` (15,000-feature vocabulary)
- Per-gap search (not career-title search) — targets the user's specific deficits
- Course level tiers: **Foundation** (5,555) → **Intermediate** (2,205) → **Advanced** (290)

---

##  Key Outputs

```python
{
  "careers": [
    {
      "occupation": "Data Scientist",
      "career_family": "Technology",
      "job_zone": 4,
      "future_proof_score": 74.2,
      "risk_category": "Low",
      "skill_alignment": 0.81,
      "demand_level": "High",
      "skills_gap": {
        "strong":   ["critical_thinking", "active_learning"],
        "moderate": ["systems_analysis"],
        "critical": ["programming", "mathematics"]
      },
      "learning_path": {
        "Foundation":    [{ "title": "Python for Everybody", "platform": "Coursera", ... }],
        "Intermediate":  [...],
        "Advanced":      [...]
      }
    }
    // ... up to 5 careers
  ],
  "transferable_skills": ["communication", "problem_solving"],
  "dashboard": {
    "sector_risk":    { ... },
    "demand_chart":   { ... }
  }
}
```

---

##  Setup & Installation

### Prerequisites

- Python 3.9+
- 4 GB RAM minimum (8 GB recommended for Sentence Transformer)

### Install Python Dependencies

```bash
pip install pandas numpy scikit-learn joblib pyarrow matplotlib seaborn
pip install sentence-transformers
```

### Place Raw Data Files

```
DATA/new/
├── Occupation Data.xlsx
├── Skills.xlsx
├── Job Zones.xlsx
├── Education, Training, and Experience.xlsx
├── bls_employment_projections.csv
├── postings.csv
├── edx_courses.csv
├── udemy_courses.csv
├── Coursera.csv
└── reviews.csv
```

### Run the Pipeline

```bash
jupyter nbconvert --to notebook --execute 01_data_understanding.ipynb --inplace
jupyter nbconvert --to notebook --execute 02_data_preparation.ipynb --inplace
jupyter nbconvert --to notebook --execute 03_career_recommendation_model_v3.ipynb --inplace
jupyter nbconvert --to notebook --execute 04_skills_gap_engine.ipynb --inplace
jupyter nbconvert --to notebook --execute 05_ai_risk_scoring.ipynb --inplace
jupyter nbconvert --to notebook --execute 06_course_recommender.ipynb --inplace
jupyter nbconvert --to notebook --execute 07_full_system_integration.ipynb --inplace
```

---

##  Usage

```python
import joblib

# Load the integrated system
system = joblib.load("models/career_system_v1.pkl")

# Define a user profile
user_input = {
    "user_type":      "graduate",          # cbc | 8-4-4 | diploma | graduate | postgraduate | professional
    "skills":         "Python, data analysis, critical thinking, research",
    "soft_skills":    "communication, teamwork",
    "cbc_pathway":    None,                # e.g. "Pure Science" or "Agriculture & Nutrition"
    "kcse_subjects":  ["Mathematics", "Biology", "Computer Studies"],
    "career_goal":    "I want to work in healthcare technology"
}

# Get recommendations
results = system.recommend(user_input)

# Top career
top = results["careers"][0]
print(f"Career:           {top['occupation']}")
print(f"Future-Proof:     {top['future_proof_score']}/100")
print(f"Risk:             {top['risk_category']}")
print(f"Critical Gaps:    {top['skills_gap']['critical']}")
```

---

##  Supported User Types

| `user_type` | Description | O\*NET Zone |
|-------------|-------------|-------------|
| `cbc` | CBC track student (Pure Science, Arts, Agriculture, etc.) | Zone 2 |
| `8-4-4` | Legacy Kenyan curriculum high school graduate | Zone 2–3 |
| `diploma` | TVET / Diploma holder | Zone 3 |
| `graduate` | University Bachelor's degree holder | Zone 4 |
| `postgraduate` | Master's or PhD holder | Zone 5 |
| `professional` | Working professional seeking career transition | Zone 4–5 |

---

##  Project Structure

```
├── DATA/
│   ├── new/                              # Raw source files (not tracked in Git)
│   └── processed/                        # Cleaned parquet outputs
├── models/                               # Serialised .pkl model artifacts
├── artifacts/                            # Config .json files
├── src/
│   ├── data_utils.py                     # Dataset loading & inspection helpers
│   ├── data_cleaning.py                  # Audit & cleaning pipeline
│   ├── skills_engineering.py             # Skill synonym map + TF-IDF utilities
│   └── Education_engineering.py          # CBC / KCSE pathway processing
├── 01_data_understanding.ipynb
├── 02_data_preparation.ipynb
├── 03_career_recommendation_model_v3.ipynb
├── 04_skills_gap_engine.ipynb
├── 05_ai_risk_scoring.ipynb
├── 06_course_recommender.ipynb
├── 07_full_system_integration.ipynb
└── README.md
```

> **Note:** Add `DATA/new/`, `DATA/processed/`, and `models/` to `.gitignore` to avoid committing large files to GitHub.

---

##  Key Design Decisions

**SOC-Code-Based Career Family Mapping**
Career families are assigned using the first 2 digits of each O\*NET SOC code rather than fuzzy string matching against BLS titles. The prior approach (cutoff=0.55) misclassified occupations like "Security Guards" → Technology and "Shoe Machine Operators" → Technology. SOC-prefix mapping is deterministic and fully authoritative.

**Sentence Transformer for Skill Matching**
`all-MiniLM-L6-v2` understands meaning rather than exact keywords — it correctly maps Swahili skill terms, Kenyan-specific skills like "crop rotation" or "litigation", and colloquial descriptions to O\*NET canonical dimensions. TF-IDF alone would fail on vocabulary mismatch.

**CBC / KCSE Implicit Skill Enrichment**
Students who cannot name formal skills explicitly receive implicit skill boosts via curriculum pathway mappings (22 CBC pathways, 28 KCSE subjects). This is critical for Kenya's target user base where self-reported skill vocabulary is limited.

**Gap-Driven Course Search**
Course recommendations are generated per skill gap rather than per career title — ensuring every recommended course directly targets a specific deficit in the user's profile.

---

##  Known Limitations

| Limitation | Impact |
|------------|--------|
| No labelled evaluation dataset | Cannot report quantitative metrics (Precision@K, NDCG) yet |
| BLS covers only 102 / 894 occupations (11.4%) | Risk scores for 88.6% of occupations are skill-model estimates, not empirical |
| `skills_abr` missing from LinkedIn data | Cannot link skills directly to demand; title-level proxy used instead |
| No course duration data available | Learning-time estimates are unavailable |
| Risk distribution skewed (96.1% Low) | Threshold calibration may need adjustment against published automation research |

---

##  Roadmap

- [ ] Build labelled evaluation dataset via user study (50–100 participants per user type)
- [ ] Integrate Frey & Osborne (2013) automation probability data for risk calibration
- [ ] Add Kenyan job board data (BrighterMonday, MyJobMag) for local demand signals
- [ ] Replace static LinkedIn batch file with LinkedIn Job Search API
- [ ] Containerise system with Docker + FastAPI for production serving
- [ ] Add course duration via platform scraping
- [ ] Build a Swahili-first mobile UI for the CBC student segment

---

##  License

This project is for academic and research use. Dataset licenses apply individually — refer to O\*NET, BLS, LinkedIn, Coursera, edX, and Udemy terms of service for data usage rights.

---

*Built with O\*NET · BLS · LinkedIn · Coursera · edX · Udemy · Kenya MoE data.*
*Sentence Transformers by HuggingFace · Modelling with scikit-learn.*
