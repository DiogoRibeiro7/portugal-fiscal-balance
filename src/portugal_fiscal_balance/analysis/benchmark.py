"""European benchmark for the subsector composition of the general-government balance.

A longitudinal study of one country can establish how Portugal behaves. It cannot
establish whether that behaviour is unusual, because it has no comparison set. ESA
2010 requires the same subsector breakdown from every reporter, so the comparison
is available and the question is answerable.

Three cautions are built into what follows.

*The non-Social-Security aggregate must include state government.* For Portugal
S.1312 does not exist and the aggregate is Central plus Local. For Germany, Spain,
Austria and Belgium it does, and omitting it would leave the identity open and
misstate the comparison. The aggregate here is therefore
S.1311 + S.1312 + S.1313, with a missing state-government tier contributing zero
because the tier does not exist rather than because a value is unknown.

*Ratios are computed in national currency.* The published percentage-of-GDP
figures carry one decimal, which is an unusable denominator for a ratio.

*This is a distribution, not a test.* Locating Portugal in a cross-country spread of
accounting compositions says how common that composition is among reporters. It
says nothing about why any country's composition takes the form it does.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

#: Sub-tiers whose balances sum to the non-Social-Security aggregate.
NON_SSF_SECTORS: Final[tuple[str, ...]] = (
    "central_government",
    "state_government",
    "local_government",
)

#: A country-year enters the benchmark only with these present.
REQUIRED_SECTORS: Final[tuple[str, ...]] = (
    "general_government",
    "central_government",
    "local_government",
    "social_security_funds",
)

#: Minimum absolute non-Social-Security balance, in percent of GDP, for the offset
#: ratio to be reported. Below this the denominator is small enough that published
#: rounding dominates the ratio, and a spuriously large value would look like a
#: finding.
OFFSET_DENOMINATOR_FLOOR_PCT_GDP: Final[float] = 0.5


def european_subsector_panel(long: pd.DataFrame) -> pd.DataFrame:
    """Build a country-year panel with the aggregates the benchmark needs."""
    values = long.pivot_table(
        index=["country", "year"], columns="sector", values="balance_mio_nac"
    )
    ratios = long.pivot_table(
        index=["country", "year"], columns="sector", values="balance_pct_gdp"
    )
    for sector in (*REQUIRED_SECTORS, "state_government"):
        if sector not in values.columns:
            values[sector] = np.nan
        if sector not in ratios.columns:
            ratios[sector] = np.nan

    panel = pd.DataFrame(index=values.index)
    panel["general_government_mio_nac"] = values["general_government"]
    panel["social_security_mio_nac"] = values["social_security_funds"]
    # A missing state-government tier means the tier does not exist, so it
    # contributes nothing; min_count keeps an all-missing row missing.
    panel["non_ssf_mio_nac"] = values[list(NON_SSF_SECTORS)].sum(axis=1, min_count=1)
    # Kept as its own column so the size of the tier is visible: it is what makes
    # including it a substantive choice rather than a formality.
    panel["state_government_mio_nac"] = values["state_government"]
    panel["general_government_pct_gdp"] = ratios["general_government"]
    panel["social_security_pct_gdp"] = ratios["social_security_funds"]
    panel["non_ssf_pct_gdp"] = ratios[list(NON_SSF_SECTORS)].sum(axis=1, min_count=1)
    panel["central_government_pct_gdp"] = ratios["central_government"]
    panel["has_state_tier"] = values["state_government"].notna()

    panel["closure_error_mio_nac"] = panel["general_government_mio_nac"] - (
        panel["non_ssf_mio_nac"] + panel["social_security_mio_nac"]
    )

    complete = long.loc[long["sector"].isin(REQUIRED_SECTORS)]
    counts = (
        complete.dropna(subset=["balance_mio_nac"])
        .groupby(["country", "year"])["sector"]
        .nunique()
        .rename("sectors_reported")
    )
    panel = panel.join(counts)

    # A missing state tier is only benign when the country has no such tier. For a
    # country that does operate one, an absent S.1312 observation is an unknown value,
    # and the sum above would silently treat it as zero while the year still counted as
    # complete. Requiring the tier wherever the country ever reports it closes that gap.
    country_reports_state_tier = (
        values["state_government"].notna().groupby(level="country").transform("any")
    )
    state_tier_available = (~country_reports_state_tier) | values["state_government"].notna()
    panel["state_tier_expected"] = country_reports_state_tier
    panel["complete"] = (
        panel["sectors_reported"].eq(len(REQUIRED_SECTORS)) & state_tier_available
    )

    panel["aggregate_positive"] = panel["general_government_mio_nac"].gt(0)
    panel["non_ssf_negative"] = panel["non_ssf_mio_nac"].lt(0)
    panel["ssf_positive"] = panel["social_security_mio_nac"].gt(0)
    panel["central_negative"] = panel["central_government_pct_gdp"].lt(0)

    # Same definition as the domestic analysis, plus a denominator floor.
    defined = (
        panel["non_ssf_negative"]
        & panel["ssf_positive"]
        & panel["non_ssf_pct_gdp"].abs().ge(OFFSET_DENOMINATOR_FLOOR_PCT_GDP)
    )
    panel["offset_ratio"] = np.where(
        defined,
        panel["social_security_mio_nac"] / panel["non_ssf_mio_nac"].abs(),
        np.nan,
    )
    panel["offset_exceeds_one"] = panel["offset_ratio"].gt(1.0)
    return panel.reset_index()


def european_benchmark_summary(panel: pd.DataFrame, *, min_years: int = 15) -> pd.DataFrame:
    """Summarise each country's composition over the years it reports completely.

    Countries with fewer than ``min_years`` complete observations are excluded:
    a frequency computed on a handful of years is not comparable with one computed
    on thirty, and including it would widen the distribution with noise. The
    excluded reporters are recoverable from the panel, so the choice is auditable.
    """
    complete = panel.loc[panel["complete"]]
    records: list[dict[str, float | int | str | bool]] = []
    for country, group in complete.groupby("country"):
        years = int(len(group))
        if years < min_years:
            continue
        surplus = group.loc[group["aggregate_positive"]]
        offset = group["offset_ratio"].dropna()
        records.append(
            {
                "country": str(country),
                "n_years": years,
                "first_year": int(group["year"].min()),
                "last_year": int(group["year"].max()),
                "has_state_tier": bool(group["has_state_tier"].any()),
                "share_central_negative": float(group["central_negative"].mean()),
                "share_ssf_positive": float(group["ssf_positive"].mean()),
                "share_aggregate_positive": float(group["aggregate_positive"].mean()),
                "n_aggregate_positive": int(len(surplus)),
                "n_aggregate_positive_with_negative_non_ssf": int(
                    surplus["non_ssf_negative"].sum()
                ),
                "mean_ssf_pct_gdp": float(group["social_security_pct_gdp"].mean()),
                "n_offset_defined": int(len(offset)),
                "median_offset_ratio": float(offset.median()) if len(offset) else np.nan,
                "share_offset_exceeds_one": (
                    float(group["offset_exceeds_one"].sum() / len(offset)) if len(offset) else np.nan
                ),
            }
        )
    return pd.DataFrame.from_records(records).sort_values("country").reset_index(drop=True)


def _percentile(values: pd.Series, target: float) -> float:
    """Return the percentile rank of ``target`` within ``values``, in percent."""
    clean = values.dropna()
    if clean.empty or not np.isfinite(target):
        return float("nan")
    return float(100.0 * (clean < target).mean())


def portugal_benchmark_position(summary: pd.DataFrame, *, country: str = "PT") -> pd.DataFrame:
    """Locate one country in each cross-country distribution.

    Returns one row per metric with the country's value, the cross-country median
    and its percentile rank, so a claim that Portugal is or is not unusual can be
    read off rather than asserted.
    """
    if country not in set(summary["country"]):
        raise ValueError(f"{country} is not present in the benchmark summary")
    target = summary.loc[summary["country"].eq(country)].iloc[0]
    metrics = {
        "share_central_negative": "Share of years with a Central Government deficit",
        "share_ssf_positive": "Share of years with a Social Security surplus",
        "share_aggregate_positive": "Share of years with an aggregate surplus",
        "mean_ssf_pct_gdp": "Mean Social Security balance (% GDP)",
        "median_offset_ratio": "Median offset ratio, where defined",
    }
    records: list[dict[str, float | int | str]] = []
    for column, label in metrics.items():
        values = summary[column]
        value = float(target[column])
        records.append(
            {
                "metric": label,
                "country_value": value,
                "cross_country_median": float(values.median()),
                "cross_country_min": float(values.min()),
                "cross_country_max": float(values.max()),
                "percentile": _percentile(values, value),
                "n_countries": int(values.notna().sum()),
            }
        )
    return pd.DataFrame.from_records(records)


#: Denominator floors swept when testing how far the offset comparison depends on
#: the one this analysis adopts.
OFFSET_FLOOR_GRID: Final[tuple[float, ...]] = (0.25, 0.50, 0.75, 1.00)


def offset_floor_sensitivity(
    panel: pd.DataFrame,
    *,
    country: str = "PT",
    floors: tuple[float, ...] = OFFSET_FLOOR_GRID,
    min_years: int = 15,
) -> pd.DataFrame:
    """Re-derive the offset comparison at several denominator floors.

    The floor keeps a near-zero denominator from manufacturing a large ratio, but its
    value is a choice rather than a property of the data. If Portugal's position moves
    with the floor, the position is an artefact of the choice; if it does not, the
    conclusion is that much firmer. Reporting the sweep is the only way a reader can
    tell which case holds.
    """
    records: list[dict[str, float | int]] = []
    for floor in floors:
        recomputed = panel.copy()
        defined = (
            recomputed["non_ssf_negative"]
            & recomputed["ssf_positive"]
            & recomputed["non_ssf_pct_gdp"].abs().ge(floor)
        )
        recomputed["offset_ratio"] = np.where(
            defined,
            recomputed["social_security_mio_nac"] / recomputed["non_ssf_mio_nac"].abs(),
            np.nan,
        )
        summary = european_benchmark_summary(recomputed, min_years=min_years)
        medians = summary["median_offset_ratio"]
        target = summary.loc[summary["country"].eq(country)]
        value = float(target["median_offset_ratio"].iloc[0]) if len(target) else np.nan
        records.append(
            {
                "floor_pct_gdp": float(floor),
                "n_defined_country_years": int(recomputed["offset_ratio"].notna().sum()),
                "n_countries": int(medians.notna().sum()),
                "country_median_offset": value,
                "cross_country_median": float(medians.median()),
                "percentile": _percentile(medians, value),
            }
        )
    return pd.DataFrame.from_records(records)


def surplus_composition_by_country(
    summary: pd.DataFrame, *, country: str = "PT"
) -> pd.DataFrame:
    """Weight the surplus-year composition by country rather than by country-year.

    Pooling every surplus country-year lets a reporter with twenty-four surplus years
    outweigh one with three. The country-weighted view asks a different and equally
    reasonable question: of a country's own surplus years, what share pair with a
    negative non-Social-Security balance? Both are reported, because they can disagree
    and neither is the obviously correct weighting.
    """
    with_surplus = summary.loc[summary["n_aggregate_positive"].gt(0)].copy()
    with_surplus["share_offsetting"] = (
        with_surplus["n_aggregate_positive_with_negative_non_ssf"]
        / with_surplus["n_aggregate_positive"]
    )
    shares = with_surplus["share_offsetting"]
    pooled_total = int(with_surplus["n_aggregate_positive"].sum())
    pooled_offsetting = int(
        with_surplus["n_aggregate_positive_with_negative_non_ssf"].sum()
    )
    target = with_surplus.loc[with_surplus["country"].eq(country)]
    value = float(target["share_offsetting"].iloc[0]) if len(target) else np.nan
    return pd.DataFrame.from_records(
        [
            {
                "n_countries_with_surplus": int(len(with_surplus)),
                "pooled_surplus_years": pooled_total,
                "pooled_offsetting_years": pooled_offsetting,
                "pooled_share": float(pooled_offsetting / pooled_total),
                "country_share": value,
                "country_weighted_median": float(shares.median()),
                "country_weighted_lower_quartile": float(shares.quantile(0.25)),
                "country_weighted_upper_quartile": float(shares.quantile(0.75)),
                "country_percentile": _percentile(shares, value),
                "n_countries_all_offsetting": int((shares >= 1.0).sum()),
            }
        ]
    )
