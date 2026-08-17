"""Shared schemas and runtime data-contract checks."""

from __future__ import annotations

from typing import Final, Literal

import pandas as pd

Sector = Literal[
    "general_government",
    "central_government",
    "regional_local_government",
    "social_security_funds",
]

SECTORS: Final[tuple[Sector, ...]] = (
    "general_government",
    "central_government",
    "regional_local_government",
    "social_security_funds",
)

BALANCE_COLUMNS: Final[tuple[str, ...]] = (
    "general_government_balance_m_eur",
    "central_government_balance_m_eur",
    "regional_local_balance_m_eur",
    "social_security_balance_m_eur",
)

ACCOUNT_METRICS: Final[tuple[str, ...]] = (
    "total_revenue_m_eur",
    "total_expenditure_m_eur",
    "balance_m_eur",
    "interest_m_eur",
    "primary_balance_m_eur",
    "gfcf_m_eur",
    "social_contributions_m_eur",
)


def require_columns(frame: pd.DataFrame, columns: list[str] | tuple[str, ...], *, name: str) -> None:
    """Raise when required columns are missing."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def require_unique_years(frame: pd.DataFrame, *, name: str) -> None:
    """Require one observation per year."""
    require_columns(frame, ["year"], name=name)
    duplicated = frame.loc[frame["year"].duplicated(), "year"].tolist()
    if duplicated:
        raise ValueError(f"{name} contains duplicated years: {duplicated}")
