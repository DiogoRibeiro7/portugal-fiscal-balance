"""Mechanism-oriented Social Security analyses."""

from __future__ import annotations

import numpy as np
import pandas as pd


def social_security_account_metrics(accounts: pd.DataFrame) -> pd.DataFrame:
    """Build long-run Social Security revenue/expenditure composition metrics."""
    frame = accounts.loc[accounts["sector"].eq("social_security_funds")].copy()
    needed = [
        "year",
        "total_revenue_m_eur",
        "total_expenditure_m_eur",
        "balance_m_eur",
        "social_contributions_m_eur",
        "nominal_gdp_m_eur",
        "statistical_regime",
    ]
    frame = frame[[column for column in needed if column in frame.columns]].dropna(
        subset=["total_revenue_m_eur", "social_contributions_m_eur"]
    )
    frame["contributions_share_total_revenue"] = (
        frame["social_contributions_m_eur"] / frame["total_revenue_m_eur"]
    )
    frame["contributions_pct_gdp"] = 100.0 * frame["social_contributions_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["revenue_pct_gdp"] = 100.0 * frame["total_revenue_m_eur"] / frame["nominal_gdp_m_eur"]
    frame["expenditure_pct_gdp"] = 100.0 * frame["total_expenditure_m_eur"] / frame["nominal_gdp_m_eur"]
    frame = frame.sort_values("year").copy()
    frame["year_gap"] = frame["year"].diff()
    frame["contribution_growth"] = frame["social_contributions_m_eur"].pct_change(fill_method=None)
    frame.loc[frame["year_gap"].ne(1), "contribution_growth"] = np.nan
    return frame.sort_values("year").reset_index(drop=True)


def social_security_internal_metrics(system_balances: pd.DataFrame, detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add simple shares to the CFP Social Security internal tables."""
    systems = system_balances.copy()
    systems["system_sum_m_eur"] = systems[
        ["citizenship_system_balance_m_eur", "previdential_system_balance_m_eur", "special_regimes_balance_m_eur"]
    ].sum(axis=1)
    details = detail.copy()
    details["previdential_contribution_share_revenue"] = (
        details["previdential_contributions_m_eur"] / details["previdential_revenue_m_eur"]
    )
    details["citizenship_lbss_transfer_share_revenue"] = np.where(
        details["citizenship_revenue_m_eur"].abs().gt(1e-9),
        details["citizenship_state_lbss_transfers_m_eur"] / details["citizenship_revenue_m_eur"],
        np.nan,
    )
    return systems, details
