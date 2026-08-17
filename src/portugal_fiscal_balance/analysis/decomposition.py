"""Exact year-to-year and revenue/expenditure decompositions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portugal_fiscal_balance.schemas import SECTOR_LABELS, STATISTICAL_REGIMES

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
    """Rank the largest annual movements inside each statistical regime.

    Ranking happens **within** a regime, not across both. Each annual change is
    computed inside one source family, so the changes themselves are sound; but a
    single table ordering historical against modern episodes by size would compare
    two methodologies, which is exactly what the rest of this analysis refuses to
    do for magnitudes. Two rankings of ``top`` episodes are produced instead.

    The attribution is hierarchical. The aggregate change is split across
    subsectors from the canonical balance panel, and then the subsector accounting
    for most of the move is itself split into its own revenue and expenditure
    changes from the detailed account panel. Earlier versions reported aggregate
    revenue and expenditure beside a subsector attribution, which invited the
    reader to connect two quantities that describe different entities.

    The two panels are different source families and measure the same aggregate
    change slightly differently; that residual is carried as its own column.

    1995 is excluded by default: the 1994-to-1995 change straddles the vintage
    splice in both panels and mixes a statistical revision with an economic
    movement.
    """
    ranked = attribution.loc[~attribution["year"].isin(exclude_years)].copy()
    ranked = ranked.dropna(subset=["aggregate_change_pct_gdp"])
    ranked["regime"] = np.where(
        ranked["year"].le(STATISTICAL_REGIMES["1977-1994_historical"][1]),
        "1977-1994_historical",
        "1995-2025_modern",
    )

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

    # Aggregate revenue and expenditure, for the source-family residual only.
    general = revenue_expenditure.loc[
        revenue_expenditure["sector"].eq("general_government"),
        ["year", "balance_change_m_eur"],
    ].rename(columns={"balance_change_m_eur": "account_balance_change_m_eur"})
    ranked = ranked.merge(general, on="year", how="left", validate="one_to_one")
    ranked["source_family_difference_m_eur"] = (
        ranked["aggregate_change_m_eur"] - ranked["account_balance_change_m_eur"]
    )

    # The hierarchical step: split the dominant subsector's own movement. Joining on
    # the sector as well as the year is what keeps the revenue and expenditure
    # figures describing the same entity as the attribution above them.
    label_to_sector = {SECTOR_LABELS[sector]: sector for sector in _CHANGE_COLUMNS.values()}
    ranked["dominant_sector_key"] = ranked["dominant_subsector"].map(label_to_sector)
    subsector = revenue_expenditure[
        ["year", "sector", "revenue_change_m_eur", "expenditure_change_m_eur"]
    ].rename(
        columns={
            "sector": "dominant_sector_key",
            "revenue_change_m_eur": "dominant_revenue_change_m_eur",
            "expenditure_change_m_eur": "dominant_expenditure_change_m_eur",
        }
    )
    ranked = ranked.merge(
        subsector, on=["year", "dominant_sector_key"], how="left", validate="one_to_one"
    )
    # Expenditure enters the balance negatively, so its contribution to the
    # subsector's movement is minus the change. Carrying both makes the sign
    # explicit instead of leaving it to the reader.
    ranked["dominant_expenditure_contribution_m_eur"] = -ranked[
        "dominant_expenditure_change_m_eur"
    ]
    ranked["dominant_split_error_m_eur"] = ranked["dominant_subsector_change_m_eur"] - (
        ranked["dominant_revenue_change_m_eur"] - ranked["dominant_expenditure_change_m_eur"]
    )

    frames: list[pd.DataFrame] = []
    for regime in STATISTICAL_REGIMES:
        window = ranked.loc[ranked["regime"].eq(regime)]
        ordered = window.reindex(
            window["aggregate_change_pct_gdp"].abs().sort_values(ascending=False).index
        )
        subset = ordered.head(top).copy()
        subset["rank_in_regime"] = range(1, len(subset) + 1)
        frames.append(subset)

    combined = pd.concat(frames, ignore_index=True)
    combined["direction"] = np.where(
        combined["aggregate_change_pct_gdp"] > 0, "improvement", "deterioration"
    )
    keep = [
        "regime",
        "rank_in_regime",
        "year",
        "direction",
        "aggregate_change_m_eur",
        "aggregate_change_pct_gdp",
        "central_change_m_eur",
        "regional_local_change_m_eur",
        "ssf_change_m_eur",
        "dominant_subsector",
        "dominant_subsector_change_m_eur",
        "dominant_subsector_share",
        "dominant_revenue_change_m_eur",
        "dominant_expenditure_change_m_eur",
        "dominant_expenditure_contribution_m_eur",
        "dominant_split_error_m_eur",
        "account_balance_change_m_eur",
        "source_family_difference_m_eur",
    ]
    return combined[keep]


#: Component schemes, by side. The two source families publish different breakdowns,
#: and the difference is not cosmetic: the modern workbooks resolve revenue into four
#: components and expenditure into seven, while the historical series resolves each
#: into current and capital only. Forcing one scheme on both would either discard the
#: modern detail or invent historical detail that does not exist.
_COMPONENT_SCHEMES: dict[str, dict[str, dict[str, str]]] = {
    "modern_detailed": {
        "revenue": {
            "social_contributions_m_eur": "Social contributions",
            "tax_revenue_m_eur": "Taxes",
            "sales_other_current_revenue_m_eur": "Sales and other current revenue",
            "capital_revenue_m_eur": "Capital revenue",
        },
        "expenditure": {
            "social_transfers_m_eur": "Social transfers",
            "compensation_m_eur": "Compensation of employees",
            "intermediate_consumption_m_eur": "Intermediate consumption",
            "subsidies_m_eur": "Subsidies",
            "interest_m_eur": "Interest",
            "other_current_expenditure_m_eur": "Other current expenditure",
            "capital_expenditure_m_eur": "Capital expenditure",
        },
    },
    "historical_current_capital": {
        "revenue": {
            "current_revenue_m_eur": "Current revenue",
            "capital_revenue_m_eur": "Capital revenue",
        },
        "expenditure": {
            "current_expenditure_m_eur": "Current expenditure",
            "capital_expenditure_m_eur": "Capital expenditure",
        },
    },
}


def account_component_changes(accounts: pd.DataFrame) -> pd.DataFrame:
    """Decompose each annual revenue and expenditure change into its components.

    Returns one row per sector-year-component in long form, because the two source
    families resolve the accounts at different depths and a wide table would need a
    column for every component of both.

    Each component carries two figures. ``change_m_eur`` is the movement in the
    component itself. ``contribution_m_eur`` is that movement's effect on the
    balance, so expenditure components are negated: a rise in social transfers
    reduces the balance. The contributions sum to the balance change; the raw
    changes do not.

    A sector-year uses whichever scheme it reports completely. Where both are
    available the detailed one is used, so the modern period is never coarsened to
    match the historical one. No change is computed across a source gap.
    """
    required = ["year", "sector", "total_revenue_m_eur", "total_expenditure_m_eur", "balance_m_eur"]
    missing = [column for column in required if column not in accounts]
    if missing:
        raise ValueError(f"accounts missing columns: {missing}")

    records: list[pd.DataFrame] = []
    for sector, group in accounts.groupby("sector", sort=False):
        data = group.sort_values("year").copy()
        adjacent = data["year"].diff().eq(1)
        balance_change = data["balance_m_eur"].diff()

        for scheme, sides in _COMPONENT_SCHEMES.items():
            columns = [column for side in sides.values() for column in side]
            if any(column not in data.columns for column in columns):
                continue
            complete = data[columns].notna().all(axis=1)
            # Both this year and the previous one must report the scheme, or the
            # difference would be taken against a missing level.
            usable = complete & complete.shift(fill_value=False) & adjacent
            if not usable.any():
                continue

            for side, labels in sides.items():
                sign = 1.0 if side == "revenue" else -1.0
                for column, label in labels.items():
                    change = data[column].diff()
                    frame = pd.DataFrame(
                        {
                            "year": data["year"],
                            "sector": sector,
                            "component_scheme": scheme,
                            "side": side,
                            "component": label,
                            "change_m_eur": change,
                            "contribution_m_eur": sign * change,
                            "balance_change_m_eur": balance_change,
                        }
                    )
                    records.append(frame.loc[usable])

    if not records:
        return pd.DataFrame(
            columns=[
                "year",
                "sector",
                "component_scheme",
                "side",
                "component",
                "change_m_eur",
                "contribution_m_eur",
                "balance_change_m_eur",
            ]
        )

    long = pd.concat(records, ignore_index=True)
    # Where a sector-year reports both schemes, keep the finer one.
    preferred = (
        long.groupby(["sector", "year"])["component_scheme"]
        .apply(lambda values: "modern_detailed" if "modern_detailed" in set(values) else values.iloc[0])
        .rename("preferred_scheme")
        .reset_index()
    )
    long = long.merge(preferred, on=["sector", "year"], how="left")
    long = long.loc[long["component_scheme"].eq(long["preferred_scheme"])].drop(
        columns="preferred_scheme"
    )

    closure = (
        long.groupby(["sector", "year"])
        .agg(
            contribution_total_m_eur=("contribution_m_eur", "sum"),
            balance_change=("balance_change_m_eur", "first"),
        )
        .reset_index()
    )
    closure["component_closure_error_m_eur"] = (
        closure["balance_change"] - closure["contribution_total_m_eur"]
    )
    long = long.merge(
        closure[["sector", "year", "component_closure_error_m_eur"]],
        on=["sector", "year"],
        how="left",
    )
    return long.sort_values(["sector", "year", "side", "component"]).reset_index(drop=True)


def episode_component_attribution(
    movements: pd.DataFrame,
    components: pd.DataFrame,
    *,
    top: int = 3,
) -> pd.DataFrame:
    """Name the component movements behind each ranked episode.

    The episodes come from :func:`largest_balance_movements` and the components from
    :func:`account_component_changes`, joined on the subsector that dominates each
    episode so that all three levels of the attribution describe one entity:
    aggregate, subsector, then that subsector's accounts.

    Components are ranked by the absolute size of their contribution to the balance
    change, so a large expenditure rise and a large revenue rise compete on the same
    footing.
    """
    label_to_sector = {SECTOR_LABELS[sector]: sector for sector in _CHANGE_COLUMNS.values()}
    episodes = movements[
        ["regime", "rank_in_regime", "year", "dominant_subsector", "dominant_subsector_change_m_eur"]
    ].copy()
    episodes["sector"] = episodes["dominant_subsector"].map(label_to_sector)

    merged = episodes.merge(
        components[["year", "sector", "component_scheme", "side", "component", "change_m_eur", "contribution_m_eur"]],
        on=["year", "sector"],
        how="left",
    )
    merged = merged.dropna(subset=["component"])
    merged["absolute_contribution"] = merged["contribution_m_eur"].abs()
    ranked = (
        merged.sort_values(["regime", "rank_in_regime", "absolute_contribution"], ascending=[True, True, False])
        .groupby(["regime", "rank_in_regime"], sort=False)
        .head(top)
        .drop(columns="absolute_contribution")
    )
    return ranked.reset_index(drop=True)


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
