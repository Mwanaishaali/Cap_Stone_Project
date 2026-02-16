# src/data_utils.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union, List

import pandas as pd


PathLike = Union[str, Path]


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    base_name: str                 # file name without extension (as seen in your DATA folder)
    file_type: Optional[str] = None  # "xlsx" | "csv" | "tsv" | None (auto)
    sheet_name: Optional[Union[str, int]] = 0  # for Excel
    read_kwargs: Optional[dict] = None


def resolve_dataset_file(data_dir: Path, base_name: str) -> Path:
    """
    Finds the actual dataset file in DATA/ even if Windows is hiding extensions.
    It searches for base_name.* and returns the first match.
    """
    matches: List[Path] = sorted(data_dir.glob(f"{base_name}.*"))
    if not matches:
        raise FileNotFoundError(
            f"Could not find a file for base name '{base_name}' inside {data_dir}. "
            f"Expected something like '{base_name}.xlsx' or '{base_name}.csv'."
        )
    return matches[0]


def infer_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return "xlsx"
    if suffix == ".csv":
        return "csv"
    if suffix in {".tsv", ".txt"}:
        return "tsv"
    # fallback
    return "csv"


def load_dataset(data_dir: Path, spec: DatasetSpec) -> pd.DataFrame:
    """
    Loads a dataset based on file type (Excel/CSV/TSV).
    """
    path = resolve_dataset_file(data_dir, spec.base_name)
    ftype = (spec.file_type or infer_file_type(path)).lower()
    read_kwargs = spec.read_kwargs or {}

    if ftype == "xlsx":
        # Default to first sheet unless specified
        return pd.read_excel(path, sheet_name=spec.sheet_name, **read_kwargs)

    if ftype == "csv":
        return pd.read_csv(path, **read_kwargs)

    if ftype == "tsv":
        return pd.read_csv(path, sep="\t", **read_kwargs)

    raise ValueError(f"Unsupported file type '{ftype}' for file: {path}")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names so merges are easier later.
    """
    out = df.copy()
    out.columns = (
        out.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )
    return out


def dataset_summary(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """
    Quick dataset-level summary.
    """
    return pd.DataFrame([{
        "dataset": name,
        "rows": len(df),
        "cols": df.shape[1],
        "duplicates": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024**2), 3),
    }])


def column_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Column-level report: dtype, missing %, unique values.
    """
    n = len(df) if len(df) else 1
    rep = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": df.isna().sum(),
        "missing_pct": (df.isna().sum() / n * 100).round(2),
        "nunique": df.nunique(dropna=True),
    }).reset_index().rename(columns={"index": "column"})
    return rep.sort_values(["missing_pct", "nunique"], ascending=[False, False])


def inspect_dataset(data_dir: Path, spec: DatasetSpec, preview_rows: int = 5) -> Dict[str, pd.DataFrame]:
    """
    One-call inspection: load + standardize columns + return summary/preview.
    """
    df = load_dataset(data_dir, spec)
    df = standardize_columns(df)

    return {
        "df": df,
        "summary": dataset_summary(df, spec.name),
        "columns": column_report(df),
        "head": df.head(preview_rows),
    }
