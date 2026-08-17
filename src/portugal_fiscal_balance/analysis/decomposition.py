"""Exact year-to-year and revenue/expenditure decompositions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portugal_fiscal_balance.schemas import SECTOR_LABELS

#: Subsector change columns, in the order they contribute to the identity.
_CHANGE_COLUMNS: dict[str, str] = {
    "central_change_m_eur": "central_government",
    "regional_local_change_m_eur": "regional_local_government",
    "ssf_change_m_eur": "social_security_funds",
}


def year_to_year_balance_attribution(panel: pd.DataFrame) -> pd.DataFrame:
    """Attribute each annual change in the aggregate balance to the three subsectors.

    Changes are reported both in million euro and scaled by current-year nominal
    GDP. The scaled columns share one denominator, so they decompose exactly:

        dB_t / GDP_t = dB^C_t / GDP_t + dB^RL_t / GDP_t + dB^SSF_t / GDP_t.

    That is deliberately *not* the change in the balance ratio, which would also
    move with the denominator and would therefore not decompose additively. The
    scaling exists only to make years comparable in size: ranking annual movements
    on nominal euro would rank them by how late they occur, since 2025 nominal GDP
    is orders of magnitude above 1977.
    """
    frame = panel.sort_values("year").copy()
    columns = {
        "general_government_balance_m_eur": "aggregate_change_m_eur",
        "central_government_balance_m_eur": "central_change_m_eur",
        "regional_local_balance_m_eur": "regional_local_change_m_eur",
        "social_security_balance_m_eur": "ssf_change_m_eur",
    }
    out = frame[["year", *columns]].copy()
    out["nominal_gdp_m_eur"] = frame["nominal_gdp_m_eur"]
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
    for column in ["aggregate_change_m_eur", *_CHANGE_COLUMNS]:
        out[column.replace("_m_eur", "_pct_gdp")] = (
            100.0 * out[column] / out["nominal_gdp_m_eur"]
        )
    return out.dropna(subset=["aggregate_change_m_eur"]).reset_index(drop=True)


def largest_balance_movements(
    attribution: pd.DataFrame,
    revenue_expenditure: pd.DataFrame,
    *,
    top: int = 5,
    exclude_years: tuple[int, ...] = (1995,),
) -> pd.DataFrame:
    """Rank the largest annual improvements and deteriorations, and attribute each one.

    Two attributions are joined for every episode. The subsector split comes from
    the canonical balance panel and closes exactly. The revenue and expenditure
    split comes from the detailed account panel, which is a different source
    family, so the two measure the same change slightly differently; the residual
    between them is carried as its own column rather than being reconciled away.

    1995 is excluded by default. The 1994-to-1995 change straddles the vintage
    splice in both panels, so it mixes a statistical revision with an economic
    movement and is not comparable with the other episodes.
    """
    ranked = attribution.loc[~attribution["year"].isin(exclude_years)].copy()
    ranked = ranked.dropna(subset=["aggregate_change_pct_gdp"])

    # Pick, for each year, the subsector with the largest absolute contribution.
    # Done with argmax over the value block rather than idxmax plus per-row
    # lookups, so the label and the value come from one index and cannot drift.
    columns = list(_CHANGE_COLUMNS)
    contributions = ranked[columns].to_numpy(dtype=float)
    dominant = np.abs(contributions).argmax(axis=1)
    labels = np.array([SECTOR_LABELS[_CHANGE_COLUMNS[column]] for column in columns])
    ranked["dominant_subsector"] = labels[dominant]
    ranked["dominant_subsector_change_m_eur"] = np.take_along_axis(
        contributions, dominant[:, None], axis=1
    ).ravel()
    ranked["dominant_subsector_share"] = np.where(
        ranked["aggregate_change_m_eur"].abs().gt(1e-9),
        ranked["dominant_subsector_change_m_eur"] / ranked["aggregate_change_m_eur"].abs(),
        np.nan,
    )

    general = revenue_expenditure.loc[
        revenue_expenditure["sector"].eq("general_government"),
        ["year", "revenue_change_m_eur", "expenditure_change_m_eur", "balance_change_m_eur"],
    ].rename(columns={"balance_change_m_eur": "account_balance_change_m_eur"})
    ranked = ranked.merge(general, on="year", how="left", validate="one_to_one")
    ranked["source_family_difference_m_eur"] = (
        ranked["aggregate_change_m_eur"] - ranked["account_balance_change_m_eur"]
    )

    frames: list[pd.DataFrame] = []
    for direction, ascending in (("improvement", False), ("deterioration", True)):
        ordered = ranked.sort_values("aggregate_change_pct_gdp", ascending=ascending)
        subset = ordered.head(top).copy()
        subset["direction"] = direction
        subset["rank"] = range(1, len(subset) + 1)
        frames.append(subset)

    keep = [
        "direction",
        "rank",
        "year",
        "aggregate_change_m_eur",
        "aggregate_change_pct_gdp",
        "central_change_m_eur",
        "regional_local_change_m_eur",
        "ssf_change_m_eur",
        "dominant_subsector",
        "dominant_subsector_share",
        "revenue_change_m_eur",
        "expenditure_change_m_eur",
        "account_balance_change_m_eur",
        "source_family_difference_m_eur",
    ]
    return pd.concat(frames, ignore_index=True)[keep]


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
