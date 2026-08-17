"""Debt-flow reconciliation diagnostics."""

from __future__ import annotations

import pandas as pd


def debt_reconciliation_table(debt: pd.DataFrame) -> pd.DataFrame:
    """Return observations with debt, debt change, balance and stock-flow adjustment."""
    required = [
        "year",
        "sector",
        "balance_m_eur",
        "stock_flow_adjustment_m_eur",
        "debt_change_m_eur",
        "debt_m_eur",
        "nominal_gdp_m_eur",
    ]
    missing = [column for column in required if column not in debt.columns]
    if missing:
        raise ValueError(f"debt data missing columns: {missing}")
    frame = debt[required].dropna().copy()
    frame["reconciliation_error_m_eur"] = (
        frame["debt_change_m_eur"] + frame["balance_m_eur"] - frame["stock_flow_adjustment_m_eur"]
    )
    frame["debt_pct_gdp"] = 100.0 * frame["debt_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["stock_flow_adjustment_pct_gdp"] = 100.0 * frame["stock_flow_adjustment_m_eur"] / frame["nominal_gdp_m_eur"]
    return frame.sort_values(["sector", "year"]).reset_index(drop=True)
