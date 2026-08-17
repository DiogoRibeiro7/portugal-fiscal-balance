"""Validation rules for extracted and processed datasets."""

from __future__ import annotations

import pandas as pd

from portugal_fiscal_balance.schemas import BALANCE_COLUMNS, SECTOR_LABELS, require_columns


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


#: Source-comparison column prefixes mapped to the sector they describe.
_COMPARISON_SECTORS: dict[str, str] = {
    "general_government": "general_government",
    "central_government": "central_government",
    "regional_local": "regional_local_government",
    "social_security": "social_security_funds",
}


def _difference_row(
    check: str, comparison: str, differences: pd.Series
) -> dict[str, float | int | str]:
    """Summarise one column of signed differences as a worst-case row."""
    finite = differences.dropna()
    if finite.empty:
        return {
            "check": check,
            "comparison": comparison,
            "n_observations": 0,
            "max_abs_difference_m_eur": float("nan"),
            "year_of_max": "--",
        }
    position = finite.abs().idxmax()
    return {
        "check": check,
        "comparison": comparison,
        "n_observations": int(len(finite)),
        "max_abs_difference_m_eur": float(finite.abs().max()),
        "year_of_max": str(position),
    }


def source_validation_summary(
    *,
    balance_panel: pd.DataFrame,
    account_checks: pd.DataFrame,
    debt: pd.DataFrame,
    source_comparison: pd.DataFrame,
    overlap: pd.DataFrame,
) -> pd.DataFrame:
    """Collect every cross-check the pipeline runs into one comparable table.

    Two different kinds of check are deliberately reported side by side, in the
    same unit, because they answer different questions and are routinely
    conflated. An *identity* check asks whether the extraction is arithmetically
    self-consistent: it can close to numerical precision while both sources are
    wrong in the same way. An *agreement* check asks whether two independently
    published sources report the same number for the same year, which identity
    closure cannot establish. The largest disagreement in the panel is a Central
    Government difference of about 67 million euro, while the identities close to
    rounding, so the distinction is not hypothetical.
    """
    rows: list[dict[str, float | int | str]] = []

    closure = balance_panel.set_index("year")["closure_error_m_eur"]
    rows.append(
        _difference_row(
            "Accounting identity",
            "Aggregate balance minus the sum of its three subsectors",
            closure,
        )
    )

    # Indexed on a readable sector label rather than the raw sector code, because
    # this index becomes a cell in the rendered report.
    identity = account_checks.copy()
    identity_series = identity.set_index(
        identity["sector"].map(SECTOR_LABELS).fillna(identity["sector"]).astype(str)
        + ", "
        + identity["year"].astype(str)
    )["identity_error_m_eur"]
    rows.append(
        _difference_row(
            "Accounting identity",
            "Revenue minus expenditure minus the recorded balance",
            identity_series,
        )
    )

    reconciliation = debt.set_index("year")["reconciliation_error_m_eur"]
    rows.append(
        _difference_row(
            "Accounting identity",
            "Debt change against minus the balance plus the stock-flow adjustment",
            reconciliation,
        )
    )

    indexed = source_comparison.set_index("year")
    for prefix, sector in _COMPARISON_SECTORS.items():
        rows.append(
            _difference_row(
                "Source agreement",
                f"PORDATA bridge against the CFP workbook, {SECTOR_LABELS[sector]}",
                indexed[f"{prefix}_source_difference_m_eur"],
            )
        )

    vintages = overlap.set_index("metric")["difference_m_eur"]
    rows.append(
        _difference_row(
            "Vintage revision",
            "1995 modern vintage against the historical vintage, four balances",
            vintages,
        )
    )
    # The vintage row indexes on a metric name rather than a year, so the
    # year-of-max column would otherwise leak a raw column identifier.
    rows[-1]["year_of_max"] = "1995"

    return pd.DataFrame.from_records(rows)
