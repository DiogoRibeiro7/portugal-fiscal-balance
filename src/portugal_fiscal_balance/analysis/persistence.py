"""Persistence, transition and run-length summaries for annual balances."""

from __future__ import annotations

from typing import cast

import pandas as pd

from portugal_fiscal_balance.schemas import SECTOR_BALANCE_PCT_GDP, STATISTICAL_REGIMES

SECTOR_BALANCES = SECTOR_BALANCE_PCT_GDP


def _state(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def persistence_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Summarise sign frequency, average magnitude and longest runs by subsector."""
    records: list[dict[str, float | int | str]] = []
    for sector, column in SECTOR_BALANCES.items():
        values = panel[["year", column]].dropna().sort_values("year")
        states = values[column].map(_state).tolist()
        longest = {"positive": 0, "negative": 0, "zero": 0}
        current_state: str | None = None
        current_len = 0
        for state in states:
            if state == current_state:
                current_len += 1
            else:
                if current_state is not None:
                    longest[current_state] = max(longest[current_state], current_len)
                current_state = state
                current_len = 1
        if current_state is not None:
            longest[current_state] = max(longest[current_state], current_len)
        records.append(
            {
                "sector": sector,
                "n_years": int(len(values)),
                "positive_years": int((values[column] > 0).sum()),
                "negative_years": int((values[column] < 0).sum()),
                "mean_balance_pct_gdp": float(values[column].mean()),
                "median_balance_pct_gdp": float(values[column].median()),
                "longest_positive_run": int(longest["positive"]),
                "longest_negative_run": int(longest["negative"]),
            }
        )
    return pd.DataFrame.from_records(records)


def persistence_by_regime(panel: pd.DataFrame) -> pd.DataFrame:
    """Split the sign and magnitude summaries by statistical regime.

    :func:`persistence_summary` averages over the whole panel, which mixes the
    historical long series with the modern national accounts. The two regimes
    differ in level, so a pooled mean describes neither of them: the aggregate
    balance averages -6.43% of GDP over 1977--1994 and -4.04% over 1995--2025,
    against a pooled -4.92%. Sign counts survive pooling much better than
    magnitudes, and both are reported here so they are read on one basis.

    Runs are deliberately not recomputed per regime. A run is a property of the
    uninterrupted series, and truncating it at an arbitrary window boundary would
    report the length of the window rather than the length of the run.
    """
    records: list[dict[str, float | int | str]] = []
    for regime, (start, end) in STATISTICAL_REGIMES.items():
        window = panel.loc[panel["year"].between(start, end)]
        for sector, column in SECTOR_BALANCES.items():
            values = window[["year", column]].dropna()
            if values.empty:
                continue
            records.append(
                {
                    "regime": regime,
                    "sector": sector,
                    "first_year": int(values["year"].min()),
                    "last_year": int(values["year"].max()),
                    "n_years": int(len(values)),
                    "positive_years": int((values[column] > 0).sum()),
                    "negative_years": int((values[column] < 0).sum()),
                    "mean_balance_pct_gdp": float(values[column].mean()),
                    "median_balance_pct_gdp": float(values[column].median()),
                    "min_balance_pct_gdp": float(values[column].min()),
                    "max_balance_pct_gdp": float(values[column].max()),
                }
            )
    return pd.DataFrame.from_records(records)


def transition_probabilities(panel: pd.DataFrame) -> pd.DataFrame:
    """Estimate empirical one-year sign transition probabilities."""
    records: list[dict[str, float | int | str]] = []
    for sector, column in SECTOR_BALANCES.items():
        states = panel[["year", column]].dropna().sort_values("year").copy()
        states["state"] = states[column].map(_state)
        states["next_state"] = states["state"].shift(-1)
        states = states.dropna(subset=["next_state"])
        counts = states.groupby(["state", "next_state"]).size().rename("n").reset_index()
        totals = counts.groupby("state")["n"].transform("sum")
        counts["probability"] = counts["n"] / totals
        counts["sector"] = sector
        transition_records = cast(
            list[dict[str, float | int | str]],
            counts[["sector", "state", "next_state", "n", "probability"]].to_dict("records"),
        )
        records.extend(transition_records)
    return pd.DataFrame.from_records(records)
