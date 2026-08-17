"""Load reproducible PORDATA/INE source snapshots bundled with the repository."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from portugal_fiscal_balance.schemas import BALANCE_COLUMNS, require_columns, require_unique_years


def load_balance_snapshot(path: Path) -> pd.DataFrame:
    """Load the 1995-2025 balance-by-subsector snapshot."""
    frame = pd.read_csv(path)
    require_columns(frame, ["year", *BALANCE_COLUMNS, "status"], name="PORDATA balance snapshot")
    require_unique_years(frame, name="PORDATA balance snapshot")
    return frame.sort_values("year").reset_index(drop=True)


def load_general_pct_snapshot(path: Path) -> pd.DataFrame:
    """Load the general-government balance-to-GDP validation snapshot."""
    frame = pd.read_csv(path)
    require_columns(frame, ["year", "general_government_balance_pct_gdp"], name="PORDATA GDP snapshot")
    require_unique_years(frame, name="PORDATA GDP snapshot")
    return frame.sort_values("year").reset_index(drop=True)
