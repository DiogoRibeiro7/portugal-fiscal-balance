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
    panel["complete"] = panel["sectors_reported"].eq(len(REQUIRED_SECTORS))

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
