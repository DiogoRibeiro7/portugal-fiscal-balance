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

SECTOR_BALANCE_PCT_GDP: Final[dict[str, str]] = {
    "general_government": "general_government_balance_pct_gdp",
    "central_government": "central_government_balance_pct_gdp",
    "regional_local_government": "regional_local_balance_pct_gdp",
    "social_security_funds": "social_security_balance_pct_gdp",
}

SECTOR_LABELS: Final[dict[str, str]] = {
    "general_government": "General Government",
    "central_government": "Central Government",
    "regional_local_government": "Regional and Local",
    "social_security_funds": "Social Security Funds",
}

#: The two statistical regimes of the canonical panel, as closed year intervals.
#:
#: Any statistic whose value depends on the level of the balance -- a mean, a
#: segment mean, a regression intercept -- must be computed inside one regime.
#: Pooling the two mixes source vintages whose levels differ, so the pooled
#: value describes neither. Sign frequencies are far more robust to pooling, but
#: they are reported per regime as well so the two are read on the same basis.
STATISTICAL_REGIMES: Final[dict[str, tuple[int, int]]] = {
    "1977-1994_historical": (1977, 1994),
    "1995-2025_modern": (1995, 2025),
}

#: Presentation labels for the regime keys, used by tables and figure legends.
#:
#: The same split is keyed two ways across the pipeline: by the window it covers
#: and by the source family that produced it. Both reach presentation tables, so
#: both are labelled here rather than falling through to a raw key.
REGIME_TABLE_LABELS: Final[dict[str, str]] = {
    "1977-1994_historical": "1977--1994 historical",
    "1995-2025_modern": "1995--2025 modern",
    "historical_long_series": "1977--1994 historical",
    "esa2010_modern": "1995--2025 modern",
}

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
