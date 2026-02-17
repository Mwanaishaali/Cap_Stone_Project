# src/data_utils.py
from __future__ import annotations  # allows using type hints like DatasetSpec without quotes (better typing behavior)

from dataclasses import dataclass  # makes it easy to define small "data container" classes
from pathlib import Path  # modern way to work with file paths (cross-platform)
from typing import Dict, Optional, Union, List  # type hints for readability and IDE support

import pandas as pd  # pandas is used to load and analyze tabular data


# A "type alias": a path can be provided either as a string or as a Path object
PathLike = Union[str, Path]


# A dataclass that stores metadata about a dataset (its name, where it is, and how to read it)
# frozen=True means once you create a DatasetSpec, you cannot modify it (immutable config object)
@dataclass(frozen=True)
class DatasetSpec:
    name: str  # display name used in reports/tables (e.g., "Coursera Reviews")
    base_name: str  # file name WITHOUT extension, as seen in  DATA folder (e.g., "reviews")
    file_type: Optional[str] = None  # optionally force "xlsx" | "csv" | "tsv"; if None we infer from extension
    sheet_name: Optional[Union[str, int]] = 0  # for Excel only: 0 = first sheet, or you can pass "Sheet1"
    read_kwargs: Optional[dict] = None  # extra options passed to pandas readers (encoding, skiprows, etc.)


def resolve_dataset_file(data_dir: Path, base_name: str) -> Path:
    """
    Finds the real dataset file inside DATA/ even if extensions are hidden (common on Windows).
    Example: base_name="reviews" matches reviews.csv or reviews.tsv or reviews.xlsx.
    Returns the first matching file found.
    """
    # Search for any file that starts with base_name and has ANY extension
    matches: List[Path] = sorted(data_dir.glob(f"{base_name}.*"))

    # If no file is found, raise an error with a helpful message
    if not matches:
        raise FileNotFoundError(
            f"Could not find a file for base name '{base_name}' inside {data_dir}. "
            f"Expected something like '{base_name}.xlsx' or '{base_name}.csv'."
        )

    # Return the first matching file (sorted makes this deterministic)
    return matches[0]


def infer_file_type(path: Path) -> str:
    """
    Infer dataset type from file extension.
    Returns: "xlsx", "csv", or "tsv" (fallback: "csv").
    """
    suffix = path.suffix.lower()  # get extension and normalize to lowercase, e.g. ".CSV" -> ".csv"

    if suffix in {".xlsx", ".xls"}:
        return "xlsx"  # Excel file
    if suffix == ".csv":
        return "csv"  # CSV file
    if suffix in {".tsv", ".txt"}:
        return "tsv"  # TSV text file (tab-separated)

    # fallback if unknown extension
    return "csv"


def load_dataset(data_dir: Path, spec: DatasetSpec) -> pd.DataFrame:
    """
    Load a dataset into a pandas DataFrame based on its file type (Excel/CSV/TSV).
    """
    # Find the actual file path inside DATA/ using base_name
    path = resolve_dataset_file(data_dir, spec.base_name)

    # Decide file type: use spec.file_type if provided, otherwise infer from file extension
    ftype = (spec.file_type or infer_file_type(path)).lower()

    # If no extra read arguments are provided, use an empty dictionary
    read_kwargs = spec.read_kwargs or {}

    # Excel loading
    if ftype == "xlsx":
        # sheet_name=0 means first sheet by default; can also be "Sheet1"
        return pd.read_excel(path, sheet_name=spec.sheet_name, **read_kwargs)

    # CSV loading
    if ftype == "csv":
        return pd.read_csv(path, **read_kwargs)

    # TSV loading (tab-separated values)
    if ftype == "tsv":
        return pd.read_csv(path, sep="\t", **read_kwargs)

    # If file type is not supported, throw an error
    raise ValueError(f"Unsupported file type '{ftype}' for file: {path}")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names so merges and references are easier later.
    Example: "Job Title" -> "job_title"
    """
    out = df.copy()  # avoid mutating the original df

    # Convert to string, trim whitespace, lowercase, replace spaces with underscores
    out.columns = (
        out.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)  # r"\s+" means one or more whitespace characters
    )

    return out


def dataset_summary(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """
    Create a one-row dataset summary: shape, duplicates, missing values, and memory usage.
    Returns a DataFrame so it displays nicely in notebooks.
    """
    return pd.DataFrame([{
        "dataset": name,  # display name
        "rows": len(df),  # number of rows
        "cols": df.shape[1],  # number of columns
        "duplicates": int(df.duplicated().sum()),  # count duplicate rows
        "missing_cells": int(df.isna().sum().sum()),  # total missing values across entire dataframe
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024**2), 3),  # approximate memory usage in MB
    }])


def column_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Column-level report:
    - dtype: data type of each column
    - missing: number of missing values
    - missing_pct: % missing values
    - nunique: number of unique values (excluding NaN)
    """
    # Avoid division by zero if df has 0 rows
    n = len(df) if len(df) else 1

    # Build per-column statistics
    rep = pd.DataFrame({
        "dtype": df.dtypes.astype(str),  # dtype per column
        "missing": df.isna().sum(),  # missing count per column
        "missing_pct": (df.isna().sum() / n * 100).round(2),  # missing percent per column
        "nunique": df.nunique(dropna=True),  # unique values per column
    }).reset_index().rename(columns={"index": "column"})  # move column names into a column called "column"

    # Sort to show worst columns first (most missing, then most unique)
    return rep.sort_values(["missing_pct", "nunique"], ascending=[False, False])


def inspect_dataset(
    data_dir: Path,
    spec: DatasetSpec,
    preview_rows: int = 5
) -> Dict[str, pd.DataFrame]:
    """
    One-call inspection helper used in the notebook.
    It:
    1) loads a dataset,
    2) standardizes column names,
    3) returns:
       - df (full dataframe)
       - summary (dataset-level summary)
       - columns (column-level report)
       - head (preview rows)
    """
    df = load_dataset(data_dir, spec)  # load data
    df = standardize_columns(df)  # standardize column names

    # Return everything needed for quick reporting in notebooks
    return {
        "df": df,
        "summary": dataset_summary(df, spec.name),
        "columns": column_report(df),
        "head": df.head(preview_rows),
    }
