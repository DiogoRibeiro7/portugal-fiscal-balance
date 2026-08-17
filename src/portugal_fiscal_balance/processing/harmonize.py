"""Harmonisation of historical and modern fiscal datasets."""

from __future__ import annotations

import pandas as pd

from portugal_fiscal_balance.schemas import BALANCE_COLUMNS, require_columns, require_unique_years


def harmonize_balance_panel(
    historical: pd.DataFrame,
    modern: pd.DataFrame,
    modern_gdp: pd.DataFrame,
) -> pd.DataFrame:
    """Create the canonical 1977-2025 balance panel without smoothing the 1995 splice."""
    require_columns(historical, ["year", *BALANCE_COLUMNS, "nominal_gdp_m_eur"], name="historical")
    require_columns(modern, ["year", *BALANCE_COLUMNS], name="modern")
    require_columns(modern_gdp, ["year", "nominal_gdp_m_eur"], name="modern_gdp")

    hist = historical.loc[historical["year"].between(1977, 1994)].copy()
    hist["source_primary"] = "Banco de Portugal / INE long series"
    hist["statistical_regime"] = "historical_long_series"

    mod = modern.loc[modern["year"].between(1995, 2025)].copy()
    mod = mod.merge(modern_gdp, on="year", how="left", validate="one_to_one")
    mod["source_primary"] = "INE via PORDATA balance snapshot"
    mod["statistical_regime"] = "modern_national_accounts"

    keep = ["year", *BALANCE_COLUMNS, "nominal_gdp_m_eur", "source_primary", "statistical_regime"]
    panel = pd.concat([hist[keep], mod[keep]], ignore_index=True).sort_values("year")
    require_unique_years(panel, name="harmonised balance panel")
    expected = list(range(1977, 2026))
    if panel["year"].tolist() != expected:
        raise ValueError("Harmonised balance panel does not cover every year from 1977 to 2025")

    for column in BALANCE_COLUMNS:
        panel[column.replace("_m_eur", "_pct_gdp")] = 100.0 * panel[column] / panel["nominal_gdp_m_eur"]

    panel["closure_error_m_eur"] = panel["general_government_balance_m_eur"] - (
        panel["central_government_balance_m_eur"]
        + panel["regional_local_balance_m_eur"]
        + panel["social_security_balance_m_eur"]
    )
    panel["closure_within_tolerance"] = panel["closure_error_m_eur"].abs().le(2.0)
    panel["known_methodology_break"] = panel["year"].eq(1995)
    return panel.reset_index(drop=True)


def build_methodology_overlap(historical: pd.DataFrame, modern: pd.DataFrame) -> pd.DataFrame:
    """Retain both 1995 vintages as an explicit overlap diagnostic."""
    hist = historical.loc[historical["year"].eq(1995)].iloc[0]
    mod = modern.loc[modern["year"].eq(1995)].iloc[0]
    records: list[dict[str, float | str]] = []
    for column in BALANCE_COLUMNS:
        records.append(
            {
                "metric": column,
                "historical_1995_m_eur": float(hist[column]),
                "modern_1995_m_eur": float(mod[column]),
                "difference_m_eur": float(mod[column] - hist[column]),
            }
        )
    return pd.DataFrame.from_records(records)


def harmonize_account_panel(historical_accounts: pd.DataFrame, modern_accounts: pd.DataFrame) -> pd.DataFrame:
    """Build an audit-friendly long account panel with source gaps left explicit.

    General Government uses the modern ESA 2010 workbook from 1995 onward. The three
    subsectors use the historical long series through 1995 and modern CFP data from
    2000 onward. No values are imputed for 1996-1999 subsector account components.
    """
    historical = historical_accounts.copy()
    modern = modern_accounts.copy()
    hist_keep = historical.loc[
        ((historical["sector"] == "general_government") & historical["year"].between(1977, 1994))
        | ((historical["sector"] != "general_government") & historical["year"].between(1977, 1995))
    ]
    modern_keep = modern.loc[
        ((modern["sector"] == "general_government") & modern["year"].between(1995, 2025))
        | ((modern["sector"] != "general_government") & modern["year"].between(2000, 2025))
    ]
    panel = pd.concat([hist_keep, modern_keep], ignore_index=True, sort=False)
    panel = panel.sort_values(["sector", "year"]).reset_index(drop=True)
    duplicates = panel.duplicated(["sector", "year"])
    if duplicates.any():
        raise ValueError("Account panel contains duplicate sector-year observations")
    return panel
