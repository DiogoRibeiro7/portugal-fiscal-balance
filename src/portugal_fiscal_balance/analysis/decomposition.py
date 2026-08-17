"""Exact year-to-year and revenue/expenditure decompositions."""

from __future__ import annotations

import numpy as np
import pandas as pd


def year_to_year_balance_attribution(panel: pd.DataFrame) -> pd.DataFrame:
    """Attribute each annual change in the aggregate balance to the three subsectors."""
    frame = panel.sort_values("year").copy()
    columns = {
        "general_government_balance_m_eur": "aggregate_change_m_eur",
        "central_government_balance_m_eur": "central_change_m_eur",
        "regional_local_balance_m_eur": "regional_local_change_m_eur",
        "social_security_balance_m_eur": "ssf_change_m_eur",
    }
    out = frame[["year", *columns]].copy()
    for source, target in columns.items():
        out[target] = frame[source].diff()
    out["change_closure_error_m_eur"] = out["aggregate_change_m_eur"] - (
        out["central_change_m_eur"] + out["regional_local_change_m_eur"] + out["ssf_change_m_eur"]
    )
    denominator = out["aggregate_change_m_eur"].abs()
    for column in ["central_change_m_eur", "regional_local_change_m_eur", "ssf_change_m_eur"]:
        out[column.replace("_m_eur", "_share_abs_aggregate_change")] = np.where(
            denominator.gt(1e-9), out[column] / denominator, np.nan
        )
    return out.dropna(subset=["aggregate_change_m_eur"]).reset_index(drop=True)


def revenue_expenditure_change_decomposition(accounts: pd.DataFrame) -> pd.DataFrame:
    """Decompose the change in balance into total-revenue and total-expenditure changes."""
    required = ["year", "sector", "total_revenue_m_eur", "total_expenditure_m_eur", "balance_m_eur"]
    missing = [column for column in required if column not in accounts]
    if missing:
        raise ValueError(f"accounts missing columns: {missing}")
    records: list[pd.DataFrame] = []
    for _sector, group in accounts.groupby("sector", sort=False):
        data = group.sort_values("year").copy()
        data["year_gap"] = data["year"].diff()
        data["revenue_change_m_eur"] = data["total_revenue_m_eur"].diff()
        data["expenditure_change_m_eur"] = data["total_expenditure_m_eur"].diff()
        data["balance_change_m_eur"] = data["balance_m_eur"].diff()
        # Do not bridge source gaps such as 1995 -> 2000 for subsector accounts.
        data.loc[data["year_gap"].ne(1), ["revenue_change_m_eur", "expenditure_change_m_eur", "balance_change_m_eur"]] = np.nan
        data["decomposition_error_m_eur"] = (
            data["balance_change_m_eur"]
            - (data["revenue_change_m_eur"] - data["expenditure_change_m_eur"])
        )
        records.append(data[["year", "sector", "year_gap", "revenue_change_m_eur", "expenditure_change_m_eur", "balance_change_m_eur", "decomposition_error_m_eur"]])
    return pd.concat(records, ignore_index=True).dropna(subset=["balance_change_m_eur"]).reset_index(drop=True)
