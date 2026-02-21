import pandas as pd
import numpy as np
import os

def load_datasets(data_folder='DATA'):
    """Finds and loads the 8 specific workforce datasets."""
    files = [
        "ai_impact_jobs_2010_2025.csv",
        "AI_Impact_on_Jobs_2030.csv",
        "ai_job_trends_dataset.csv",
        "career_dataset_large.xlsx",
        "Coursera.csv",
        "reviews.csv",
        "reviews_by_course.csv",
        "cbc_data.csv",  
    ]
    datasets = {}
    for file in files:
        path = os.path.join(data_folder, file)
        if os.path.exists(path):
            datasets[file] = pd.read_csv(path) if file.endswith('.csv') else pd.read_excel(path)
        else:
            print(f"WARNING: {file} not found in {data_folder}")
    return datasets


# ---------------------------------------------------------------------------

OUTLIER_STRATEGY = {
    "reviews.csv":           "clip_rating",   # CHANGED from "cap"
    "reviews_by_course.csv": "clip_rating",   # CHANGED from "cap"
    "Coursera.csv":          "clip_rating",   # ADDED  — was inconsistently omitted
    # Everything else → "flag"
}

# FIX Issue 1: bounds used by the clip_rating strategy
RATING_COLUMNS = {"label", "rate", "rating"}
RATING_MIN, RATING_MAX = 1, 5


def _iqr_bounds(series: pd.Series):
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def clean_and_audit(df, name, dataset_file: str = ""):
    """
    Clean and audit a dataset following CRISP-DM Data Preparation best practices.

    Parameters
    ----------
    df           : raw DataFrame
    name         : human-readable label used in the audit report
    dataset_file : original filename (used to pick the outlier strategy).
                   Pass the key you used in load_datasets(), e.g. 'reviews.csv'.

    Outlier handling
    ----------------
    • job / career datasets  → FLAG only  (real extremes must not be lost)
    • review / aggregation   → CAP (winsorise to IQR bounds); row is kept

    Returns
    -------
    (cleaned_df, audit_report_df)
    """

    df = df.copy()
    strategy = OUTLIER_STRATEGY.get(dataset_file, "flag")

    # ------------------------------------------------------------------
    # PRE-CLEANING SNAPSHOT
    # ------------------------------------------------------------------
    nums = df.select_dtypes(include=[np.number]).columns
    outliers_before = sum(
        ((df[col] < _iqr_bounds(df[col])[0]) | (df[col] > _iqr_bounds(df[col])[1])).sum()
        for col in nums
    )

    before = {
        "dataset":          name,
        "state":            "Raw",
        "rows":             len(df),
        "nulls":            int(df.isnull().sum().sum()),
        "dupes":            int(df.duplicated().sum()),
        "outliers":         int(outliers_before),
        
    }

    # ------------------------------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------------------------------
    df = df.drop_duplicates().copy()

    # ------------------------------------------------------------------
    # HANDLE MISSING VALUES
    # ------------------------------------------------------------------
    for col in df.columns:
        if df[col].dtype == "object":
            # FIX Issue 2: categorical text columns correctly filled with "Unknown".
            # Median imputation is undefined for text; this was the original bug.
            # For high-missingness text cols (ai_keywords, ai_skills) a binary
            # presence flag is also created so the signal is not lost.
            pct_missing = df[col].isna().mean()
            if pct_missing > 0.5:
                flag_col = f"has_{col}"
                df[flag_col] = df[col].notna().astype(int)   # 1=was present, 0=was missing
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = df[col].fillna(df[col].median())

    # ------------------------------------------------------------------
    # STANDARDISE COLUMN NAMES
    # ------------------------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # ------------------------------------------------------------------
    # OUTLIER HANDLING
    # ------------------------------------------------------------------
    nums_clean = df.select_dtypes(include=[np.number]).columns
    outliers_after = 0
    capped_cells   = 0

    for col in nums_clean:
        lower, upper = _iqr_bounds(df[col])
        is_outlier = (df[col] < lower) | (df[col] > upper)
        outliers_after += is_outlier.sum()

        if strategy == "clip_rating" and col in RATING_COLUMNS:
            # FIX Issue 1: domain clip for ordinal rating columns [1, 5].
            # Only values outside the known valid range are errors.
            capped = is_outlier.sum()
            df[col] = df[col].clip(lower=RATING_MIN, upper=RATING_MAX)
            capped_cells += capped
            df[f"{col}_was_clipped"] = is_outlier.astype(int)

        elif strategy == "cap":
            # Winsorise: clamp extreme values to IQR bounds (numeric cols only)
            capped = is_outlier.sum()
            df[col] = df[col].clip(lower=lower, upper=upper)
            capped_cells += capped
            # Still flag so downstream steps know which rows were adjusted
            df[f"{col}_was_capped"] = is_outlier.astype(int)

        else:  # strategy == "flag" or non-rating col in clip_rating dataset
            # Leave the value untouched; just add a boolean flag column
            df[f"{col}_is_outlier"] = is_outlier.astype(int)

    # After capping, outlier count should be 0 for capped datasets
    outliers_after_final = 0
    for col in nums_clean:
        lower, upper = _iqr_bounds(df[col])
        outliers_after_final += ((df[col] < lower) | (df[col] > upper)).sum()

    # ------------------------------------------------------------------
    # POST-CLEANING SNAPSHOT
    # ------------------------------------------------------------------
    after = {
        "dataset":          name,
        "state":            "Cleaned",
        "rows":             len(df),
        "nulls":            int(df.isnull().sum().sum()),
        "dupes":            int(df.duplicated().sum()),
        "outliers":         int(outliers_after_final),
    
    }

    if strategy == "cap" and capped_cells:
        after["cells_capped"] = int(capped_cells)

    return df, pd.DataFrame([before, after])
