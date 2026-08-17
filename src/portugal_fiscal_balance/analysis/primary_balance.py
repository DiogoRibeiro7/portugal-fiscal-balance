"""Primary-balance and investment diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def primary_balance_table(accounts: pd.DataFrame) -> pd.DataFrame:
    """Compare headline and primary balances wherever interest data are available."""
    columns = [
        "year",
        "sector",
        "balance_m_eur",
        "interest_m_eur",
        "primary_balance_m_eur",
        "nominal_gdp_m_eur",
        "statistical_regime",
    ]
    frame = accounts[[column for column in columns if column in accounts.columns]].copy()
    frame = frame.dropna(subset=["balance_m_eur", "interest_m_eur", "nominal_gdp_m_eur"])
    frame["primary_balance_recomputed_m_eur"] = frame["balance_m_eur"] + frame["interest_m_eur"]
    frame["primary_balance_identity_error_m_eur"] = (
        frame["primary_balance_m_eur"] - frame["primary_balance_recomputed_m_eur"]
    )
    frame["interest_pct_gdp"] = 100.0 * frame["interest_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["primary_balance_pct_gdp"] = 100.0 * frame["primary_balance_recomputed_m_eur"] / frame["nominal_gdp_m_eur"]
    return frame.sort_values(["sector", "year"]).reset_index(drop=True)


def investment_diagnostic(accounts: pd.DataFrame) -> pd.DataFrame:
    """Compute a transparent analytical balance before GFCF.

    The result is not an official fiscal indicator. It simply adds GFCF back to B.9
    to quantify how large fixed-capital formation is relative to the observed balance.
    """
    required = ["year", "sector", "balance_m_eur", "gfcf_m_eur", "nominal_gdp_m_eur"]
    frame = accounts[required].dropna().copy()
    frame["balance_before_gfcf_m_eur"] = frame["balance_m_eur"] + frame["gfcf_m_eur"]
    frame["gfcf_pct_gdp"] = 100.0 * frame["gfcf_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["balance_before_gfcf_pct_gdp"] = 100.0 * frame["balance_before_gfcf_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["gfcf_share_abs_balance"] = np.where(
        frame["balance_m_eur"].abs().gt(1e-9),
        frame["gfcf_m_eur"] / frame["balance_m_eur"].abs(),
        np.nan,
    )
    return frame.sort_values(["sector", "year"]).reset_index(drop=True)
