"""
download_assets.py
==================
Downloads model artifacts from Google Drive when running on Render.
Run automatically via render.yaml before uvicorn starts.

Set this environment variable in Render dashboard:
  GDRIVE_FOLDER_ID  →  the ID of your careeriq-model-data Google Drive folder
"""
from __future__ import annotations

import os
import sys
import zipfile
import shutil
from pathlib import Path

# ── gdown is a lightweight Google Drive downloader ───────────────────────────
try:
    import gdown
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
    import gdown


# ── Paths (Render mounts project at /opt/render/project/src) ─────────────────
BASE   = Path("/opt/render/project/src")
MODELS = BASE / "models"
ARTS   = BASE / "artifacts"
PROC   = BASE / "DATA" / "processed"


def already_downloaded() -> bool:
    """Check if real model files are present and non-empty."""
    marker = PROC / "master_occupation_profiles.parquet"
    if not marker.exists():
        return False
    # Also verify it's not empty (more than 10KB)
    if marker.stat().st_size < 10_000:
        return False
    pkl_files = list(MODELS.glob("*.pkl"))
    if len(pkl_files) < 5:
        return False
    return True


def download_folder(folder_id: str, dest: Path, name: str):
    """Download a Google Drive folder recursively using gdown."""
    dest.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    print(f"  📥  Downloading {name} → {dest}")
    gdown.download_folder(url=url, output=str(dest), quiet=False, use_cookies=False)
    print(f"  ✅  {name} downloaded")


def main():
    # ── Read sub-folder IDs from environment ─────────────────────────────────
    # Set these in Render → Environment Variables
    models_id = os.environ.get("GDRIVE_MODELS_ID")
    arts_id   = os.environ.get("GDRIVE_ARTIFACTS_ID")
    proc_id   = os.environ.get("GDRIVE_PROCESSED_ID")

    if not any([models_id, arts_id, proc_id]):
        print("⚠️  No GDRIVE_*_ID environment variables set — skipping asset download.")
        print("    The API will start with demo data.")
        return

    if already_downloaded():
        print("✅  Assets already present — skipping download.")
        return

    print("🚀  Starting asset download from Google Drive…")

    if models_id:
        download_folder(models_id, MODELS, "models")
    if arts_id:
        download_folder(arts_id, ARTS, "artifacts")
    if proc_id:
        download_folder(proc_id, PROC, "DATA/processed")

    print("\n✅  All assets downloaded successfully.")
    print(f"   Models    : {list(MODELS.glob('*.pkl')).__len__()} pkl files")
    print(f"   Artifacts : {list(ARTS.glob('*.json')).__len__()} json files")
    print(f"   Processed : {list(PROC.glob('*.parquet')).__len__()} parquet files")


if __name__ == "__main__":
    main()
