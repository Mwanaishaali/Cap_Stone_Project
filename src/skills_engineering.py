import pandas as pd
import re
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# ==========================================================
# SKILL COLUMN ALIASES
# columns we recognise as skill sources across all datasets
# ==========================================================
SKILL_COLUMN_ALIASES = [
    'skills',
    'core_skills',
    'ai_skills',
    'gained skills',
    'gained_skills',
    'skill',
    'key_skills',
    'required_skills',
    'top_skills',
]

# Columns created by THIS script — never treat as raw skill inputs
INTERNAL_COLUMNS = {'skill_list', 'skill_count', 'skills_combined'}

# Path where the fitted TF-IDF vectoriser is saved
TFIDF_SAVE_PATH = "models/tfidf_skills.joblib"


# ==========================================================
# DETECT AND MERGE SKILL COLUMNS
# ==========================================================
def _get_skills_series(df):
    """
    Finds all skill-related columns in a dataframe and merges
    them into a single combined text series per row.
    Returns (combined_series, list_of_columns_found).
    """
    col_lower_map = {c.lower(): c for c in df.columns}
    found_cols = []

    # exact alias matches first
    for alias in SKILL_COLUMN_ALIASES:
        if alias.lower() in col_lower_map:
            found_cols.append(col_lower_map[alias.lower()])

    # any column whose name contains 'skill' not already found
    for col in df.columns:
        if 'skill' in col.lower() and col not in found_cols:
            if col.lower() in INTERNAL_COLUMNS:
                continue
            numeric_ratio = pd.to_numeric(df[col], errors='coerce').notna().mean()
            if numeric_ratio > 0.8:
                continue
            found_cols.append(col)

    if not found_cols:
        return None, []

    print(f"✔ Skill columns detected: {found_cols}")

    merged = df[found_cols].fillna('').astype(str)
    combined = merged.apply(
        lambda row: ', '.join(v for v in row if v.strip() and v.lower() != 'nan'),
        axis=1
    )

    return combined, found_cols


# ==========================================================
# TEXT CLEANING
# ==========================================================
def _clean_skill_text(series):
    """
    Lowercases, strips whitespace, and normalises separators.
    """
    return (
        series
        .str.lower()
        .str.strip()
        .str.replace(r'[;/|&]', ',', regex=True)
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )


# ==========================================================
# SKILL TOKEN BUILDER
# converts skill list into clean tokens for TF-IDF
# multi-word skills become single tokens: machine learning -> machine_learning
# this prevents meaningless cross-skill bigrams in the vocabulary
# ==========================================================
def _build_skill_tokens(skill_list_series):
    """
    Takes a Series of Python lists (skill_list) and converts each
    skill into an underscore-joined token so TF-IDF treats
    'machine learning' as one feature not two separate words.

    Example:
        ['machine learning', 'python', 'data analysis']
        -> 'machine_learning python data_analysis'
    """
    return skill_list_series.apply(
        lambda skills: ' '.join(s.strip().replace(' ', '_') for s in skills if s.strip())
    )


# ==========================================================
# PREPARE DATASET
# run this on any dataset before fitting or transforming
# ==========================================================
def prepare_skills(df):
    """
    Extracts skill columns, cleans text, and adds:
        skills_combined — cleaned merged skill text
        skill_list      — Python list of individual skills
        skill_count     — number of skills per row
        skill_tokens    — underscore-joined tokens for TF-IDF input

    Returns (enriched_df, skill_tokens_series).
    Returns (df, None) if no skill columns found.
    """
    df = df.copy()

    if 'skill_count' in df.columns:
        print(" Dataset already prepared. Skipping.")
        # still return skill_tokens if they exist
        if 'skill_tokens' in df.columns:
            return df, df['skill_tokens']
        return df, None

    skills_series, cols = _get_skills_series(df)

    if skills_series is None:
        print(" No skill columns found — skipping.")
        return df, None

    skills_series = _clean_skill_text(skills_series)

    df['skills_combined'] = skills_series

    df['skill_list'] = skills_series.apply(
        lambda x: [s.strip() for s in x.split(',') if s.strip()]
    )

    df['skill_count'] = df['skill_list'].apply(len)

    # Build clean underscore tokens for TF-IDF
    df['skill_tokens'] = _build_skill_tokens(df['skill_list'])

    return df, df['skill_tokens']


# ==========================================================
# FIT — call ONLY on career_dataset (training data)
# ==========================================================
def fit_tfidf_skills(df, max_features=100, save=True):
    """
    Fits a TF-IDF vectoriser on career_dataset skill tokens.

    IMPORTANT: Call this ONLY on your training dataset.
    Use transform_tfidf_skills() for everything else.

    Parameters
    ----------
    df           : career_dataset DataFrame
    max_features : max vocabulary features to keep (default 100)
    save         : save fitted vectoriser to TFIDF_SAVE_PATH (default True)

    Returns
    -------
    tfidf    : fitted TfidfVectorizer
    tfidf_df : DataFrame of TF-IDF feature columns ready to concat
    """
    df, skill_tokens = prepare_skills(df)

    if skill_tokens is None:
        raise ValueError("No skill columns found. Cannot fit TF-IDF.")

    # ngram_range=(1,1) because each skill is already one clean token
    # sublinear_tf reduces dominance of very common skills
    tfidf = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 1),
        min_df=2,
        sublinear_tf=True
    )

    matrix = tfidf.fit_transform(skill_tokens)

    feature_names = [f"skill_tfidf_{f}" for f in tfidf.get_feature_names_out()]
    tfidf_df = pd.DataFrame(
        matrix.toarray(),
        columns=feature_names,
        index=df.index
    )

    print(f"✔ TF-IDF fitted on {len(df)} rows")
    print(f"  Vocabulary size : {len(tfidf.vocabulary_)}")
    print(f"  Features created: {len(feature_names)}")
    print(f"  Top 20 features : {list(tfidf.get_feature_names_out()[:20])}")

    if save:
        os.makedirs(os.path.dirname(TFIDF_SAVE_PATH), exist_ok=True)
        joblib.dump(tfidf, TFIDF_SAVE_PATH)
        print(f"  Saved -> {TFIDF_SAVE_PATH}")

    return tfidf, tfidf_df


# ==========================================================
# TRANSFORM — call on test data or any other dataset
# ==========================================================
def transform_tfidf_skills(df, tfidf):
    """
    Transforms skills using an already-fitted TF-IDF vectoriser.
    Never re-fits.

    Parameters
    ----------
    df    : any DataFrame with a skill column
    tfidf : fitted TfidfVectorizer from fit_tfidf_skills()

    Returns
    -------
    tfidf_df : DataFrame of TF-IDF feature columns ready to concat
    """
    df, skill_tokens = prepare_skills(df)

    feature_names = [f"skill_tfidf_{f}" for f in tfidf.get_feature_names_out()]

    if skill_tokens is None:
        print(" No skill columns found — returning zero TF-IDF frame.")
        return pd.DataFrame(0, index=df.index, columns=feature_names)

    matrix = tfidf.transform(skill_tokens)

    tfidf_df = pd.DataFrame(
        matrix.toarray(),
        columns=feature_names,
        index=df.index
    )

    print(f"✔ TF-IDF transformed {len(df)} rows → {len(feature_names)} features")
    return tfidf_df


# ==========================================================
# PROCESS — convenience wrapper for the notebook loop
# ==========================================================
def process_skills(df, tfidf=None, is_fit_dataset=False, save=True):
    """
    Convenience wrapper used in the notebook skills loop.
    Calls fit or transform automatically based on is_fit_dataset.

    Parameters
    ----------
    df             : DataFrame to process
    tfidf          : fitted TfidfVectorizer (None only when is_fit_dataset=True)
    is_fit_dataset : True ONLY for career_dataset
    save           : save vectoriser after fitting (default True)

    Returns
    -------
    df_enriched : df with skill_list, skill_count, skill_tokens added
    tfidf_df    : TF-IDF feature DataFrame to concat onto X matrix
    tfidf       : the TfidfVectorizer (fitted or passed through)
    """
    if is_fit_dataset:
        tfidf, tfidf_df = fit_tfidf_skills(df, save=save)
    else:
        if tfidf is None:
            raise ValueError(
                "tfidf must be provided when is_fit_dataset=False. "
                "Run process_skills on career_dataset first."
            )
        tfidf_df = transform_tfidf_skills(df, tfidf)

    df_enriched, _ = prepare_skills(df)

    return df_enriched, tfidf_df, tfidf


# ==========================================================
# INSPECTION HELPERS — notebook reporting only
# ==========================================================
def skills_summary(df, tfidf_df=None):
    """Prints a quick summary of skill coverage for a dataset."""
    print("\n===== SKILL SUMMARY =====")
    print(f"Rows        : {len(df)}")

    if 'skill_count' in df.columns:
        print(f"Avg skills  : {round(df['skill_count'].mean(), 2)}")
        print(f"Max skills  : {df['skill_count'].max()}")
        print(f"Zero skills : {(df['skill_count'] == 0).sum()} rows")

    if tfidf_df is not None:
        non_zero = (tfidf_df != 0).sum(axis=1)
        print(f"Avg active TF-IDF features per row: {round(non_zero.mean(), 2)}")


def preview_skills(df, n=5):
    """Shows a sample of skill_list values for spot-checking."""
    cols = [c for c in ['job_title', 'career', 'occupation',
                         'skill_list', 'skill_count'] if c in df.columns]
    print("\n===== SAMPLE SKILL ROWS =====")
    print(df[cols].head(n).to_string())
