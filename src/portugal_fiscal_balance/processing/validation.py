"""Validation rules for extracted and processed datasets."""

from __future__ import annotations

import pandas as pd

from portugal_fiscal_balance.schemas import BALANCE_COLUMNS, require_columns


def validate_balance_panel(panel: pd.DataFrame) -> dict[str, float | bool | int]:
    """Validate annual coverage, finite values and the subsector accounting identity."""
    require_columns(panel, ["year", *BALANCE_COLUMNS, "closure_error_m_eur"], name="balance panel")
    if panel["year"].tolist() != list(range(1977, 2026)):
        raise ValueError("Balance panel must cover 1977-2025 without gaps")
    if panel[list(BALANCE_COLUMNS)].isna().any().any():
        raise ValueError("Balance panel contains missing balance observations")
    max_error = float(panel["closure_error_m_eur"].abs().max())
    return {
        "n_years": int(len(panel)),
        "max_abs_closure_error_m_eur": max_error,
        "all_closures_within_2m_eur": bool(max_error <= 2.0),
    }


def validate_accounts(accounts: pd.DataFrame, *, tolerance_m_eur: float = 2.0) -> pd.DataFrame:
    """Return sector-year account identity diagnostics instead of silently dropping failures."""
    required = ["year", "sector", "total_revenue_m_eur", "total_expenditure_m_eur", "balance_m_eur"]
    require_columns(accounts, required, name="account panel")
    diagnostics = accounts[required].copy()
    diagnostics["identity_error_m_eur"] = (
        diagnostics["total_revenue_m_eur"]
        - diagnostics["total_expenditure_m_eur"]
        - diagnostics["balance_m_eur"]
    )
    diagnostics["within_tolerance"] = diagnostics["identity_error_m_eur"].abs().le(tolerance_m_eur)
    return diagnostics


def compare_modern_balance_sources(
    modern_primary: pd.DataFrame,
    cfp_general: pd.DataFrame,
    cfp_subsectors: pd.DataFrame,
) -> pd.DataFrame:
    """Compare the rounded PORDATA/INE balance bridge with CFP ESA 2010 workbooks."""
    merged = modern_primary.merge(
        cfp_general[["year", "general_government_balance_m_eur"]].rename(
            columns={"general_government_balance_m_eur": "cfp_general_government_balance_m_eur"}
        ),
        on="year",
        how="left",
        validate="one_to_one",
    )
    renamed = cfp_subsectors.rename(
        columns={
            "central_government_balance_m_eur": "cfp_central_government_balance_m_eur",
            "regional_local_balance_m_eur": "cfp_regional_local_balance_m_eur",
            "social_security_balance_m_eur": "cfp_social_security_balance_m_eur",
        }
    )
    merged = merged.merge(
        renamed[
            [
                "year",
                "cfp_central_government_balance_m_eur",
                "cfp_regional_local_balance_m_eur",
                "cfp_social_security_balance_m_eur",
            ]
        ],
        on="year",
        how="left",
        validate="one_to_one",
    )
    for prefix in ("general_government", "central_government", "regional_local", "social_security"):
        merged[f"{prefix}_source_difference_m_eur"] = (
            merged[f"{prefix}_balance_m_eur"] - merged[f"cfp_{prefix}_balance_m_eur"]
        )
    return merged
