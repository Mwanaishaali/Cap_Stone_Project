
education_map = {
    'Unknown':     0,   # no change
    'High School': 1,   # no change
    'Bachelors':   2,   # CHANGED from 4 → 2 (consecutive after High School)
    'Masters':     3,   # CHANGED from 5 → 3
    'Doctorate':   4,   # CHANGED from 6 → 4
    # Certificate and Diploma kept for CERT_EDUCATION_FLOOR rescue logic only
    'Certificate': 1,   # treated same as High School floor
    'Diploma':     2,   # treated same as Bachelors floor
}

# ---------------------------------------------------------------------------
# Certification → minimum implied education level
# If someone holds a professional cert, we can infer at least that level.
# ---------------------------------------------------------------------------
CERT_EDUCATION_FLOOR = {
    # Professional / graduate-level certs imply at least Bachelors
    'AWS Certified':          'Bachelors',
    'Google Data Analytics':  'Bachelors',
    'CFA Level 1':            'Bachelors',
    'Digital Marketing':      'Certificate',
    'Tally ERP':              'Certificate',
    'Mental Health Basics':   'Certificate',
    'Creative Writing':       'Certificate',
}

import pandas as pd
import numpy as np
import re

def process_education(df):
    """
    Clean, standardize and encode education levels.
    Also uses the Certifications column (when present) to rescue rows
    that would otherwise be classified as 'Unknown'.
    Optimized for ML training and deployment.
    """

    df = df.copy()

    # ------------------------------------------------------------------
    # 0. Column aliasing
    #    Support both 'education_level' (snake_case) and
    #    'Education Level' (title-case, e.g. career_dataset_large.xlsx)
    # ------------------------------------------------------------------
    edu_col  = None
    cert_col = None

    for col in df.columns:
        if col.lower().replace(' ', '_') == 'education_level':
            edu_col = col
        if col.lower().replace(' ', '_') == 'certifications':
            cert_col = col

    if edu_col is None:
        
        # ai_job_trends that have 'required_education' instead of 'education_level'.
        # The caller (02_data_preparation.ipynb) must now pass datasets with
        # 'required_education' after renaming the column, OR call process_education
        # directly with that column aliased. See notebook Step 3 for the rename.
        return df                          # nothing to process

    # Work on a normalised internal column; keep the original intact
    df['education_level'] = (
        df[edu_col]
        .fillna('Unknown')
        .astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r'[^\w\s]', '', regex=True)   # B.Sc → bsc
    )

    # ------------------------------------------------------------------
    # 1. Vectorised classification
    #    Added:  matric / o-level   → High School
    #            intermediate / a-level / fscs / fsc → High School
    # ------------------------------------------------------------------
    conditions = [
        df['education_level'].str.contains(r'phd|doctorate|doctoral',                          regex=True, na=False),
        df['education_level'].str.contains(r'master|msc|ma\b|mba|postgrad|graduate',           regex=True, na=False),
        df['education_level'].str.contains(r'bachelor|bsc|ba\b|beng|undergrad|degree',         regex=True, na=False),
        df['education_level'].str.contains(r'diploma',                                          regex=True, na=False),
        df['education_level'].str.contains(r'certificate|cert',                                 regex=True, na=False),
        df['education_level'].str.contains(
            r'high school|kcse|form 4|secondary|alevel|olevel|matric|intermediate|fsc|fscs',
            regex=True, na=False
        ),
    ]

    categories = [
        'Doctorate',
        'Masters',
        'Bachelors',
        'Diploma',
        'Certificate',
        'High School',
    ]

    df['education_category'] = pd.Series(
        np.select(conditions, categories, default='Unknown'),
        index=df.index
    )

    # ------------------------------------------------------------------
    # 2. Certifications-based rescue
    #    For rows still labelled 'Unknown', check the Certifications
    #    column and apply the implied education floor from CERT_EDUCATION_FLOOR.
    # ------------------------------------------------------------------
    if cert_col is not None:
        cert_series = df[cert_col].fillna('').astype(str).str.strip()

        unknown_mask = df['education_category'] == 'Unknown'

        if unknown_mask.any():
            # Map each certification to its education floor
            implied = cert_series[unknown_mask].map(CERT_EDUCATION_FLOOR)

            # Only overwrite where we actually have a mapping
            has_mapping = implied.notna()
            df.loc[unknown_mask & has_mapping, 'education_category'] = implied[has_mapping]

    # ------------------------------------------------------------------
    # 3. Certifications-based upgrade
    #    Even for known rows, a high-level cert can signal a higher
    #    minimum education than what was recorded.
    #    Example: 'CFA Level 1' holder recorded as 'High School'
    #             → upgrade to 'Bachelors' (the floor for that cert).
    # ------------------------------------------------------------------
    if cert_col is not None:
        cert_series = df[cert_col].fillna('').astype(str).str.strip()
        implied_all = cert_series.map(CERT_EDUCATION_FLOOR)

        upgrade_mask = implied_all.notna()
        if upgrade_mask.any():
            current_encoded  = df.loc[upgrade_mask, 'education_category'].map(education_map).fillna(0)
            implied_encoded  = implied_all[upgrade_mask].map(education_map).fillna(0)

            should_upgrade   = implied_encoded > current_encoded
            upgrade_idx      = upgrade_mask[upgrade_mask].index[should_upgrade]

            df.loc[upgrade_idx, 'education_category'] = implied_all[upgrade_idx]

    # ------------------------------------------------------------------
    # 4. Ordinal encoding (for ML)
    # ------------------------------------------------------------------
    df['education_encoded'] = df['education_category'].map(education_map)

    return df
CBC_PATHWAY_EDUCATION_MAP = {
    'TVET':            'Certificate',
    'Business':        'Bachelors',
    'Social Sciences': 'Bachelors',
    'Sciences':        'Bachelors',
    'Arts':            'Bachelors',
}

def process_cbc_education(df):
    """
    Creates an education_level column from CBC pathway column
    so process_education() can pick it up automatically.
    """
    if 'pathway' not in df.columns:
        return df
    df = df.copy()
    df['education_level'] = (
        df['pathway']
        .map(CBC_PATHWAY_EDUCATION_MAP)
        .fillna('Unknown')
    )
    return df