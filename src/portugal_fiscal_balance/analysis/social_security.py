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


def ssf_accounting_boundary_comparison(
    balance_panel: pd.DataFrame,
    system_balances: pd.DataFrame,
) -> pd.DataFrame:
    """Place the ESA 2010 Social Security balance beside the CFP budget-system total.

    The two quantities are not the same object. The ESA 2010 Social Security Funds
    balance is the B.9 term that enters the general-government identity; the CFP
    systems are budget-execution aggregates with a different accounting boundary.
    They are therefore never added, netted or reconciled here.

    What this table does is measure how far apart they are, year by year. The gap
    is small relative to the balances but it is non-zero in every overlapping year,
    which is precisely why the two must not be substituted for one another: a
    figure quoted from the budget documents is not the figure that appears in the
    national accounts.
    """
    systems = system_balances.copy()
    components = [
        "previdential_system_balance_m_eur",
        "citizenship_system_balance_m_eur",
        "special_regimes_balance_m_eur",
    ]
    systems["budget_system_total_m_eur"] = systems[components].sum(axis=1)
    merged = systems.merge(
        balance_panel[["year", "social_security_balance_m_eur"]].rename(
            columns={"social_security_balance_m_eur": "esa2010_ssf_balance_m_eur"}
        ),
        on="year",
        how="left",
        validate="one_to_one",
    )
    merged["boundary_difference_m_eur"] = (
        merged["esa2010_ssf_balance_m_eur"] - merged["budget_system_total_m_eur"]
    )
    merged["boundary_difference_share_esa_balance"] = np.where(
        merged["esa2010_ssf_balance_m_eur"].abs().gt(1e-9),
        merged["boundary_difference_m_eur"] / merged["esa2010_ssf_balance_m_eur"].abs(),
        np.nan,
    )
    keep = [
        "year",
        "esa2010_ssf_balance_m_eur",
        "budget_system_total_m_eur",
        *components,
        "boundary_difference_m_eur",
        "boundary_difference_share_esa_balance",
    ]
    return merged[keep].sort_values("year").reset_index(drop=True)


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
