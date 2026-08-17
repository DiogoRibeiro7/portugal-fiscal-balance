"""Neutral accounting metrics for the annual balance panel."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from portugal_fiscal_balance.schemas import BALANCE_COLUMNS, require_columns


def compute_balance_metrics(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute offset and contribution metrics without causal or normative interpretation."""
    require_columns(panel, ["year", *BALANCE_COLUMNS, "nominal_gdp_m_eur"], name="balance panel")
    result = panel.copy()
    result["non_ssf_balance_m_eur"] = (
        result["central_government_balance_m_eur"] + result["regional_local_balance_m_eur"]
    )
    result["non_ssf_balance_pct_gdp"] = 100.0 * result["non_ssf_balance_m_eur"] / result["nominal_gdp_m_eur"]
    result["aggregate_balance_positive"] = result["general_government_balance_m_eur"].gt(0)
    result["ssf_balance_positive"] = result["social_security_balance_m_eur"].gt(0)
    result["non_ssf_balance_negative"] = result["non_ssf_balance_m_eur"].lt(0)
    result["positive_aggregate_with_negative_non_ssf_balance"] = (
        result["aggregate_balance_positive"]
        & result["ssf_balance_positive"]
        & result["non_ssf_balance_negative"]
    )
    result["ssf_exceeds_aggregate_balance"] = (
        result["aggregate_balance_positive"]
        & result["social_security_balance_m_eur"].gt(result["general_government_balance_m_eur"])
    )
    result["ssf_share_of_positive_aggregate_balance"] = np.where(
        result["aggregate_balance_positive"],
        result["social_security_balance_m_eur"] / result["general_government_balance_m_eur"],
        np.nan,
    )
    result["ssf_required_to_offset_non_ssf_m_eur"] = np.where(
        result["non_ssf_balance_m_eur"].lt(0), result["non_ssf_balance_m_eur"].abs(), 0.0
    )
    result["ssf_offset_ratio"] = np.where(
        result["non_ssf_balance_negative"] & result["ssf_balance_positive"],
        result["social_security_balance_m_eur"] / result["non_ssf_balance_m_eur"].abs(),
        np.nan,
    )
    result["ssf_balance_after_offset_m_eur"] = (
        result["social_security_balance_m_eur"] - result["ssf_required_to_offset_non_ssf_m_eur"]
    )
    for column in [
        "general_government_balance_pct_gdp",
        "central_government_balance_pct_gdp",
        "regional_local_balance_pct_gdp",
        "social_security_balance_pct_gdp",
        "non_ssf_balance_pct_gdp",
    ]:
        result[f"{column.removesuffix('_pct_gdp')}_5y_mean_pct_gdp"] = result[column].rolling(
            5, min_periods=3
        ).mean()
    return result


def summarize_balance_metrics(annual: pd.DataFrame) -> dict[str, Any]:
    """Create a compact JSON-serialisable summary."""
    surplus = annual.loc[annual["aggregate_balance_positive"]]
    offset = annual.loc[annual["positive_aggregate_with_negative_non_ssf_balance"]]
    latest = annual.loc[annual["year"].eq(2025)].iloc[0]
    return {
        "analysis_start_year": int(annual["year"].min()),
        "analysis_end_year": int(annual["year"].max()),
        "n_years": int(len(annual)),
        "positive_aggregate_balance_years": [int(v) for v in surplus["year"]],
        "positive_aggregate_with_negative_non_ssf_years": [int(v) for v in offset["year"]],
        "latest_2025": {
            "general_government_balance_m_eur": float(latest["general_government_balance_m_eur"]),
            "central_government_balance_m_eur": float(latest["central_government_balance_m_eur"]),
            "regional_local_balance_m_eur": float(latest["regional_local_balance_m_eur"]),
            "social_security_balance_m_eur": float(latest["social_security_balance_m_eur"]),
            "non_ssf_balance_m_eur": float(latest["non_ssf_balance_m_eur"]),
            "ssf_offset_ratio": float(latest["ssf_offset_ratio"]),
        },
    }
