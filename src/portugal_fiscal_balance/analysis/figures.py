"""Publication-ready figures generated from processed analysis tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _finish(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def plot_long_run_balances(panel: pd.DataFrame, path: Path) -> None:
    """Plot all four balance ratios from 1977 onward."""
    plt.figure(figsize=(11, 6))
    plt.plot(panel["year"], panel["general_government_balance_pct_gdp"], label="General Government")
    plt.plot(panel["year"], panel["central_government_balance_pct_gdp"], label="Central Government")
    plt.plot(panel["year"], panel["regional_local_balance_pct_gdp"], label="Regional and Local")
    plt.plot(panel["year"], panel["social_security_balance_pct_gdp"], label="Social Security Funds")
    plt.axhline(0, linewidth=0.8)
    plt.axvline(1995, linewidth=0.8, linestyle="--")
    plt.xlabel("Year")
    plt.ylabel("Net lending (+) / net borrowing (-), % GDP")
    plt.title("Portugal: fiscal balance by subsector, 1977–2025")
    plt.legend()
    _finish(path)


def plot_offset_ratio(metrics: pd.DataFrame, path: Path) -> None:
    """Plot the SSF offset ratio where both numerator and denominator are defined."""
    frame = metrics.dropna(subset=["ssf_offset_ratio"])
    plt.figure(figsize=(11, 5))
    plt.plot(frame["year"], frame["ssf_offset_ratio"], marker="o")
    plt.axhline(1.0, linewidth=0.8, linestyle="--")
    plt.xlabel("Year")
    plt.ylabel("SSF balance / |non-SSF balance|")
    plt.title("Social Security Funds offset ratio")
    _finish(path)


def plot_balance_change_attribution(changes: pd.DataFrame, path: Path) -> None:
    """Plot annual changes in each subsector balance."""
    recent = changes.loc[changes["year"].ge(2000)].copy()
    plt.figure(figsize=(11, 6))
    plt.plot(recent["year"], recent["central_change_m_eur"], label="Central")
    plt.plot(recent["year"], recent["regional_local_change_m_eur"], label="Regional/Local")
    plt.plot(recent["year"], recent["ssf_change_m_eur"], label="Social Security Funds")
    plt.axhline(0, linewidth=0.8)
    plt.xlabel("Year")
    plt.ylabel("Annual change, million euro")
    plt.title("Year-to-year change in subsector balances")
    plt.legend()
    _finish(path)


def plot_revenue_expenditure(accounts: pd.DataFrame, sector: str, path: Path) -> None:
    """Plot revenue, expenditure and balance as shares of GDP for one sector."""
    frame = accounts.loc[accounts["sector"].eq(sector)].dropna(
        subset=["total_revenue_pct_gdp", "total_expenditure_pct_gdp", "balance_pct_gdp"]
    )
    plt.figure(figsize=(11, 6))
    plt.plot(frame["year"], frame["total_revenue_pct_gdp"], label="Revenue")
    plt.plot(frame["year"], frame["total_expenditure_pct_gdp"], label="Expenditure")
    plt.plot(frame["year"], frame["balance_pct_gdp"], label="Balance")
    plt.axhline(0, linewidth=0.8)
    plt.xlabel("Year")
    plt.ylabel("% GDP")
    plt.title(f"Revenue, expenditure and balance: {sector.replace('_', ' ').title()}")
    plt.legend()
    _finish(path)


def plot_primary_vs_headline(primary: pd.DataFrame, sector: str, path: Path) -> None:
    """Plot headline and primary balance ratios."""
    frame = primary.loc[primary["sector"].eq(sector)]
    plt.figure(figsize=(11, 5))
    plt.plot(frame["year"], 100.0 * frame["balance_m_eur"] / frame["nominal_gdp_m_eur"], label="Headline balance")
    plt.plot(frame["year"], frame["primary_balance_pct_gdp"], label="Primary balance")
    plt.axhline(0, linewidth=0.8)
    plt.xlabel("Year")
    plt.ylabel("% GDP")
    plt.title(f"Headline versus primary balance: {sector.replace('_', ' ').title()}")
    plt.legend()
    _finish(path)


def plot_social_security_contributions(ssf: pd.DataFrame, path: Path) -> None:
    """Plot contribution share of Social Security Funds revenue."""
    frame = ssf.dropna(subset=["contributions_share_total_revenue"])
    plt.figure(figsize=(11, 5))
    plt.plot(frame["year"], 100.0 * frame["contributions_share_total_revenue"], marker="o")
    plt.xlabel("Year")
    plt.ylabel("Social contributions, % total SSF revenue")
    plt.title("Composition of Social Security Funds revenue")
    _finish(path)


def plot_debt_reconciliation(debt: pd.DataFrame, path: Path) -> None:
    """Plot General Government debt ratio and stock-flow adjustment."""
    frame = debt.loc[debt["sector"].eq("general_government")]
    plt.figure(figsize=(11, 5))
    plt.plot(frame["year"], frame["debt_pct_gdp"], label="Debt")
    plt.plot(frame["year"], frame["stock_flow_adjustment_pct_gdp"], label="Stock-flow adjustment")
    plt.axhline(0, linewidth=0.8)
    plt.xlabel("Year")
    plt.ylabel("% GDP")
    plt.title("General Government debt and stock-flow adjustment")
    plt.legend()
    _finish(path)
