"""Repository path helpers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"
TABLES = OUTPUTS / "tables"
FIGURES = OUTPUTS / "figures"
METRICS = OUTPUTS / "metrics"
REPORT = ROOT / "report"
NOTEBOOKS = ROOT / "notebooks"


def ensure_directories() -> None:
    """Create all generated-data and output directories."""
    for path in (INTERIM, PROCESSED, TABLES, FIGURES, METRICS, REPORT, NOTEBOOKS):
        path.mkdir(parents=True, exist_ok=True)
