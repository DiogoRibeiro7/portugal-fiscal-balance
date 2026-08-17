"""Generated inputs for the scientific manuscript in ``paper/``.

The manuscript and the technical report are different products. ``report.tex`` is
generated end to end: its prose is a thin restatement of persisted artefacts, and
nothing in it is authored by hand. A paper cannot work that way -- it needs an
argument, a literature position and a narrative that no template produces.

But the repository's central contract still has to hold: no number may be
transcribed by hand. So the manuscript is split in two.

``paper/sections/*.tex``
    Authored prose. Committed, hand-written, reviewed like any other text.

``paper/generated/*.tex``
    Written by this module from the same artefacts the report reads. Never edited
    by hand.

The bridge between them is ``macros.tex``: every quantity the prose needs is
exposed as a LaTeX command, so a sentence reads ``\\SsfPositiveYears of
\\PanelYears years`` rather than ``43 of 49``. If a later data vintage changes the
count, the sentence changes with it, and a stale number cannot survive in the
text. A macro that no longer exists fails the build rather than rendering silently
as nothing, which is what makes the guarantee enforceable instead of aspirational.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from portugal_fiscal_balance.reporting import latex

# The underscored helpers are reused deliberately. They are private to the
# `reporting` package rather than to `render` itself, and they encode the
# presentation rules both documents must share: canonical sector ordering, sector
# and regime labels, and column selection with renaming. Re-implementing them here
# is the alternative, and it would let the paper and the report drift apart in
# exactly the way this module exists to prevent.
from portugal_fiscal_balance.reporting.render import (  # noqa: PLC2701
    ReportInputs,
    _label_regimes,
    _label_sectors,
    _latest,
    _sector_row,
    _view,
    load,
)
from portugal_fiscal_balance.schemas import SECTOR_LABELS

#: Ordered regime keys, so "historical" and "modern" are never mixed up by position.
_HISTORICAL = "1977-1994_historical"
_MODERN = "1995-2025_modern"


def _money(value: Any) -> str:
    """Format a million-euro quantity for prose."""
    return latex.number(float(value), 0)


def _ratio(value: Any, digits: int = 2) -> str:
    """Format a plain decimal for prose."""
    return f"{float(value):.{digits}f}"


def _year_words(years: list[int]) -> str:
    """Render a list of years as running prose."""
    if not years:
        return "none"
    if len(years) == 1:
        return str(years[0])
    return ", ".join(str(year) for year in years[:-1]) + f" and {years[-1]}"


def _regime_mean(frame: pd.DataFrame, sector: str, regime: str) -> float:
    """Read one regime mean from the per-regime persistence summary."""
    selected = frame.loc[frame["sector"].eq(sector) & frame["regime"].eq(regime)]
    return float(selected.iloc[0]["mean_balance_pct_gdp"])


def build_macros(data: ReportInputs) -> dict[str, str]:
    """Build every quantity the authored prose is allowed to reference.

    Keys become LaTeX command names, so they are letters only: no digits and no
    underscores, which ``\\newcommand`` will not accept.
    """
    annual = data.annual
    latest = _latest(annual)
    positive_years = [
        int(year) for year in data.summary["balance_summary"]["positive_aggregate_balance_years"]
    ]
    central_persistence = _sector_row(data.persistence, "central_government")
    ssf_persistence = _sector_row(data.persistence, "social_security_funds")
    regional_persistence = _sector_row(data.persistence, "regional_local_government")
    central_primary = _sector_row(data.primary_signs, "central_government")
    primary_positive = [
        int(year)
        for year in str(central_primary["primary_positive_year_list"]).split(";")
        if year not in ("", "nan")
    ]
    boundary_latest = _latest(data.ss_boundary)
    provisional = [
        int(year) for year in data.balances.loc[data.balances["vintage_status"].eq("provisional"), "year"]
    ]

    agreement = data.validation_summary.loc[data.validation_summary["check"].eq("Source agreement")]
    worst_agreement = agreement.loc[agreement["max_abs_difference_m_eur"].idxmax()]
    identities = data.validation_summary.loc[
        data.validation_summary["check"].eq("Accounting identity")
    ]

    stability = data.break_stability.merge(
        data.breaks[["regime", "sector", "break_years"]],
        on=["regime", "sector"],
        how="left",
        validate="one_to_one",
    )
    matches = (
        stability["break_years"].fillna("").astype("string")
        == stability["modal_break_years"].fillna("").astype("string")
    )
    weakest = stability.loc[stability["modal_break_years_share"].idxmin()]

    scaled = data.movements["aggregate_change_pct_gdp"]
    top_improvement = data.movements.loc[scaled.idxmax()]
    top_deterioration = data.movements.loc[scaled.idxmin()]

    latest_ssf_accounts = _latest(data.ssf)
    systems_first = data.ss_systems.sort_values("year").iloc[0]
    systems_latest = _latest(data.ss_systems)

    # How close General Government and Central Government actually track, rather
    # than an appeal to how close they look on a chart.
    aggregate_ratio = data.balances["general_government_balance_pct_gdp"]
    central_ratio = data.balances["central_government_balance_pct_gdp"]

    # Sign robustness, verified rather than asserted. A methodological revision
    # could in principle flip a small balance across zero; in the two overlaps this
    # panel retains, none does.
    overlap_signs = int(
        (
            np.sign(data.overlap["historical_1995_m_eur"])
            == np.sign(data.overlap["modern_1995_m_eur"])
        ).sum()
    )
    comparison = data.source_comparison
    agreeing = 0
    compared = 0
    for prefix in ("general_government", "central_government", "regional_local", "social_security"):
        left = comparison[f"{prefix}_balance_m_eur"]
        right = comparison[f"cfp_{prefix}_balance_m_eur"]
        both = left.notna() & right.notna()
        compared += int(both.sum())
        agreeing += int((np.sign(left[both]) == np.sign(right[both])).sum())

    # The latest annual change in the Social Security balance, by account.
    ssf_change_latest = _latest(data.ss_change)

    # European benchmark. The structural comparison is the share of a country's
    # aggregate-surplus years in which the non-Social-Security balance was negative:
    # the direct cross-country analogue of this paper's headline composition.
    summary = data.benchmark_summary
    portugal = summary.loc[summary["country"].eq("PT")].iloc[0]
    with_surplus = summary.loc[summary["n_aggregate_positive"].gt(0)].copy()
    with_surplus["share_offsetting"] = (
        with_surplus["n_aggregate_positive_with_negative_non_ssf"]
        / with_surplus["n_aggregate_positive"]
    )
    all_offsetting = with_surplus.loc[with_surplus["share_offsetting"].ge(1.0)]
    position = data.benchmark_position.set_index("metric")
    ssf_share_row = position.loc["Share of years with a Social Security surplus"]
    ssf_mean_row = position.loc["Mean Social Security balance (% GDP)"]
    offset_row = position.loc["Median offset ratio, where defined"]
    central_row = position.loc["Share of years with a Central Government deficit"]
    central_always = summary.loc[summary["share_central_negative"].ge(1.0)]

    macros: dict[str, str] = {
        # Build identity. Deliberately the repository version and not a build date:
        # the pipeline is deterministic and its outputs are committed, so the
        # manuscript must not change when it is rebuilt from unchanged inputs.
        "RepositoryVersion": data.version,
        # Panel extent.
        "PanelStart": str(int(annual["year"].min())),
        "PanelEnd": str(int(annual["year"].max())),
        "PanelYears": str(int(data.summary["balance_validation"]["n_years"])),
        "AccountObservations": str(int(data.summary["n_account_observations"])),
        "GapYears": str(int(data.summary["n_subsector_account_gap_years_1996_1999"])),
        "ProvisionalYears": _year_words(provisional),
        # Sign frequencies over the whole panel.
        "NumPositiveYears": str(len(positive_years)),
        "PositiveYearList": _year_words(positive_years),
        "CentralNegativeYears": str(int(central_persistence["negative_years"])),
        "SsfPositiveYears": str(int(ssf_persistence["positive_years"])),
        "SsfNegativeYears": str(int(ssf_persistence["negative_years"])),
        "SsfLongestPositiveRun": str(int(ssf_persistence["longest_positive_run"])),
        "RegionalPositiveYears": str(int(regional_persistence["positive_years"])),
        # Magnitudes, per regime, never pooled.
        "GgMeanHistorical": _ratio(_regime_mean(data.regime_persistence, "general_government", _HISTORICAL)),
        "GgMeanModern": _ratio(_regime_mean(data.regime_persistence, "general_government", _MODERN)),
        "GgMeanPooled": _ratio(_sector_row(data.persistence, "general_government")["mean_balance_pct_gdp"]),
        "CentralMeanHistorical": _ratio(_regime_mean(data.regime_persistence, "central_government", _HISTORICAL)),
        "CentralMeanModern": _ratio(_regime_mean(data.regime_persistence, "central_government", _MODERN)),
        "SsfMeanHistorical": _ratio(_regime_mean(data.regime_persistence, "social_security_funds", _HISTORICAL)),
        "SsfMeanModern": _ratio(_regime_mean(data.regime_persistence, "social_security_funds", _MODERN)),
        # The identity in the most recent year.
        "LatestYear": str(int(latest["year"])),
        "LatestGg": _money(latest["general_government_balance_m_eur"]),
        "LatestCentral": _money(latest["central_government_balance_m_eur"]),
        "LatestRegional": _money(latest["regional_local_balance_m_eur"]),
        "LatestSsf": _money(latest["social_security_balance_m_eur"]),
        "LatestNonSsf": _money(latest["non_ssf_balance_m_eur"]),
        "LatestOffset": _ratio(latest["ssf_offset_ratio"], 3),
        "LatestGgPct": _ratio(latest["general_government_balance_pct_gdp"]),
        "LatestSsfPct": _ratio(latest["social_security_balance_pct_gdp"]),
        # Primary balance.
        "PrimaryObservedYears": str(int(central_primary["n_years"])),
        "PrimaryHeadlineNegative": str(int(central_primary["headline_negative_years"])),
        "PrimaryPositiveYears": str(int(central_primary["primary_positive_years"])),
        "PrimaryPositiveList": _year_words(primary_positive),
        "PrimaryPositiveFirst": str(min(primary_positive)) if primary_positive else "none",
        "PrimaryPositiveLast": str(max(primary_positive)) if primary_positive else "none",
        "InterestMeanPct": _ratio(central_primary["mean_interest_pct_gdp"]),
        "InterestPeakPct": _ratio(central_primary["max_interest_pct_gdp"]),
        # Social Security: national accounts and the budget systems.
        "ContributionSharePct": _ratio(
            float(latest_ssf_accounts["contributions_share_total_revenue"]) * 100.0
        ),
        "PrevidentialFirstYear": str(int(systems_first["year"])),
        "PrevidentialFirst": _money(systems_first["previdential_system_balance_m_eur"]),
        "PrevidentialLatest": _money(systems_latest["previdential_system_balance_m_eur"]),
        "CitizenshipLatest": _money(systems_latest["citizenship_system_balance_m_eur"]),
        "SsfEsaLatest": _money(boundary_latest["esa2010_ssf_balance_m_eur"]),
        "SsfBudgetLatest": _money(boundary_latest["budget_system_total_m_eur"]),
        "SsfBoundaryLatest": _money(boundary_latest["boundary_difference_m_eur"]),
        "SsfBoundaryMin": _money(data.ss_boundary["boundary_difference_m_eur"].min()),
        "SsfBoundaryMax": _money(data.ss_boundary["boundary_difference_m_eur"].max()),
        "SsfBoundaryYears": str(int(len(data.ss_boundary))),
        # Validation.
        "MaxClosureResidual": _ratio(identities["max_abs_difference_m_eur"].max()),
        "MaxSourceDisagreement": _ratio(worst_agreement["max_abs_difference_m_eur"], 1),
        "SourceDisagreementWhere": str(worst_agreement["year_of_max"]),
        # Change points.
        "BreakSeries": str(int(len(stability))),
        "BreakModalAgree": str(int(matches.sum())),
        "BreakSpecifications": str(int(stability["n_specifications"].iloc[0])),
        "WeakestBreakSector": SECTOR_LABELS[str(weakest["sector"])],
        "WeakestBreakShare": _ratio(float(weakest["modal_break_years_share"]) * 100.0, 0),
        "WeakestBreakSets": str(int(weakest["n_distinct_break_year_sets"])),
        # Ranked annual movements.
        "TopImprovementYear": str(int(top_improvement["year"])),
        "TopImprovementPct": _ratio(top_improvement["aggregate_change_pct_gdp"]),
        "TopDeteriorationYear": str(int(top_deterioration["year"])),
        "TopDeteriorationPct": _ratio(top_deterioration["aggregate_change_pct_gdp"]),
        "MovementsPerRegime": str(int(data.movements["rank_in_regime"].max())),
        # How closely the aggregate tracks Central Government.
        "AggregateCentralCorrelation": _ratio(aggregate_ratio.corr(central_ratio), 3),
        "AggregateCentralMedianGap": _ratio((aggregate_ratio - central_ratio).abs().median()),
        # Sign robustness across the retained source overlaps.
        "OverlapSignAgreements": str(overlap_signs),
        "OverlapSignTotal": str(int(len(data.overlap))),
        "SourceSignAgreements": str(agreeing),
        "SourceSignComparisons": str(compared),
        # The latest annual movement in the Social Security balance, by account.
        "SsfChangeYear": str(int(ssf_change_latest["year"])),
        "SsfChangeTotal": _money(ssf_change_latest["balance_change_m_eur"]),
        "SsfChangeContributions": _money(ssf_change_latest["contributions_contribution_m_eur"]),
        "SsfChangeOtherRevenue": _money(ssf_change_latest["other_revenue_contribution_m_eur"]),
        "SsfChangeTransfers": _money(ssf_change_latest["social_transfers_contribution_m_eur"]),
        "SsfChangeOtherExpenditure": _money(
            ssf_change_latest["other_expenditure_contribution_m_eur"]
        ),
        # European benchmark.
        "BenchmarkCountries": str(int(len(summary))),
        "BenchmarkStart": str(int(summary["first_year"].min())),
        "BenchmarkEnd": str(int(summary["last_year"].max())),
        "BenchmarkYears": str(int(portugal["n_years"])),
        "PtSsfPositiveShare": _ratio(float(portugal["share_ssf_positive"]) * 100.0, 1),
        "PtSsfShareMedian": _ratio(float(ssf_share_row["cross_country_median"]) * 100.0, 1),
        "PtSsfSharePercentile": _ratio(ssf_share_row["percentile"], 0),
        "PtSsfMeanPct": _ratio(portugal["mean_ssf_pct_gdp"]),
        "PtSsfMeanMedian": _ratio(ssf_mean_row["cross_country_median"]),
        "PtSsfMeanPercentile": _ratio(ssf_mean_row["percentile"], 0),
        "PtCentralNegativeShare": _ratio(float(portugal["share_central_negative"]) * 100.0, 0),
        "PtCentralPercentile": _ratio(central_row["percentile"], 0),
        "CentralAlwaysNegativeCountries": str(int(len(central_always))),
        "PtOffsetMedian": _ratio(portugal["median_offset_ratio"], 3),
        "OffsetMedianAcrossCountries": _ratio(offset_row["cross_country_median"], 3),
        "PtOffsetPercentile": _ratio(offset_row["percentile"], 0),
        # The structural comparison.
        "PtSurplusYears": str(int(portugal["n_aggregate_positive"])),
        "PtSurplusOffsetting": str(int(portugal["n_aggregate_positive_with_negative_non_ssf"])),
        "CountriesWithSurplus": str(int(len(with_surplus))),
        "CountriesAllOffsetting": str(int(len(all_offsetting))),
        "SurplusYearsTotal": str(int(with_surplus["n_aggregate_positive"].sum())),
        "SurplusYearsOffsetting": str(
            int(with_surplus["n_aggregate_positive_with_negative_non_ssf"].sum())
        ),
        "SurplusOffsettingShare": _ratio(
            100.0
            * float(with_surplus["n_aggregate_positive_with_negative_non_ssf"].sum())
            / float(with_surplus["n_aggregate_positive"].sum()),
            0,
        ),
    }
    return macros


def _macro_file(macros: dict[str, str]) -> str:
    """Render the macro definitions, with a guard against silent omissions."""
    lines = [
        "% Generated by portugal_fiscal_balance.reporting.paper. Do not edit.",
        "%",
        "% Every quantity the authored prose may cite is defined here from a persisted",
        "% artefact. Editing this file by hand would break the guarantee that no number",
        "% in the manuscript is transcribed.",
        "",
    ]
    for name, value in macros.items():
        lines.append(rf"\newcommand{{\{name}}}{{{value}}}")
    return "\n".join(lines) + "\n"


def _table_files(data: ReportInputs) -> dict[str, str]:
    """Build the manuscript's tables, each as a standalone includable file.

    The selection is deliberately narrower than the report's. A paper carries the
    evidence its argument needs; the report carries everything the pipeline can
    compute, and remains the place to look for the rest.
    """
    composition = _view(
        _label_regimes(_label_sectors(data.regime_persistence)),
        {
            "regime": "Regime",
            "sector": "Subsector",
            "n_years": "N",
            "positive_years": "Positive",
            "negative_years": "Negative",
            "mean_balance_pct_gdp": "Mean (\\% GDP)",
            "median_balance_pct_gdp": "Median (\\% GDP)",
        },
    )
    positive = _view(
        data.annual.loc[
            data.annual["year"].isin(
                [int(y) for y in data.summary["balance_summary"]["positive_aggregate_balance_years"]]
            )
        ],
        {
            "year": "Year",
            "general_government_balance_m_eur": "GG (M EUR)",
            "central_government_balance_m_eur": "Central (M EUR)",
            "regional_local_balance_m_eur": "Regional/local (M EUR)",
            "social_security_balance_m_eur": "SSF (M EUR)",
            "non_ssf_balance_m_eur": "Non-SSF (M EUR)",
            "ssf_offset_ratio": "Offset ratio",
        },
    )
    movements = _view(
        _label_regimes(data.movements),
        {
            "regime": "Regime",
            "rank_in_regime": "Rank",
            "year": "Year",
            "aggregate_change_pct_gdp": "Change (\\% GDP)",
            "central_change_m_eur": "Central (M EUR)",
            "regional_local_change_m_eur": "Regional/local (M EUR)",
            "ssf_change_m_eur": "SSF (M EUR)",
            "dominant_subsector": "Largest contributor",
        },
    )
    hierarchy = _view(
        _label_regimes(data.movements),
        {
            "regime": "Regime",
            "year": "Year",
            "dominant_subsector": "Largest contributor",
            "dominant_subsector_change_m_eur": "Its balance change (M EUR)",
            "dominant_revenue_change_m_eur": "$\\Delta$ revenue (M EUR)",
            "dominant_expenditure_change_m_eur": "$\\Delta$ expenditure (M EUR)",
            "dominant_expenditure_contribution_m_eur": "Expenditure contribution (M EUR)",
        },
    )
    ssf_change = _view(
        data.ss_change.loc[data.ss_change["year"].ge(2018)],
        {
            "year": "Year",
            "balance_change_m_eur": "Change in balance (M EUR)",
            "contributions_contribution_m_eur": "Social contributions (M EUR)",
            "other_revenue_contribution_m_eur": "Other revenue (M EUR)",
            "social_transfers_contribution_m_eur": "Social transfers (M EUR)",
            "other_expenditure_contribution_m_eur": "Other expenditure (M EUR)",
        },
    )
    signs = _view(
        _label_sectors(data.primary_signs),
        {
            "sector": "Subsector",
            "n_years": "N",
            "headline_negative_years": "Headline $<0$",
            "primary_positive_years": "Primary $>0$",
            "mean_interest_pct_gdp": "Mean interest (\\% GDP)",
            "max_interest_pct_gdp": "Peak interest (\\% GDP)",
        },
    )
    boundary = _view(
        data.ss_boundary,
        {
            "year": "Year",
            "esa2010_ssf_balance_m_eur": "ESA 2010 (M EUR)",
            "budget_system_total_m_eur": "Budget systems (M EUR)",
            "previdential_system_balance_m_eur": "Previdential (M EUR)",
            "citizenship_system_balance_m_eur": "Citizenship (M EUR)",
            "boundary_difference_m_eur": "Difference (M EUR)",
        },
    )
    validation = _view(
        data.validation_summary,
        {
            "check": "Check",
            "comparison": "Quantity compared",
            "n_observations": "N",
            "max_abs_difference_m_eur": "Largest absolute difference (M EUR)",
            "year_of_max": "Where",
        },
    )
    stability = _view(
        _label_regimes(_label_sectors(data.break_stability)),
        {
            "regime": "Regime",
            "sector": "Subsector",
            "modal_n_breaks": "Modal breaks",
            "modal_break_years": "Modal dates",
            "modal_break_years_share": "Share at modal dates",
            "n_distinct_break_year_sets": "Distinct date sets",
        },
    )
    stability["Modal dates"] = (
        stability["Modal dates"].astype("string").str.replace(";", ", ", regex=False)
    )
    benchmark = data.benchmark_summary.copy()
    benchmark["share_offsetting"] = np.where(
        benchmark["n_aggregate_positive"].gt(0),
        benchmark["n_aggregate_positive_with_negative_non_ssf"]
        / benchmark["n_aggregate_positive"],
        np.nan,
    )
    benchmark_view = _view(
        benchmark.sort_values("share_ssf_positive", ascending=False),
        {
            "country": "Reporter",
            "n_years": "N",
            "share_central_negative": "Central $<0$",
            "share_ssf_positive": "SSF $>0$",
            "mean_ssf_pct_gdp": "Mean SSF (\\% GDP)",
            "n_aggregate_positive": "Surplus years",
            "n_aggregate_positive_with_negative_non_ssf": "of which non-SSF $<0$",
            "median_offset_ratio": "Median offset",
        },
    )
    position_view = _view(
        data.benchmark_position,
        {
            "metric": "Metric",
            "country_value": "Portugal",
            "cross_country_median": "Cross-country median",
            "cross_country_min": "Minimum",
            "cross_country_max": "Maximum",
            "percentile": "Percentile",
        },
    )
    coverage_source = data.accounts.groupby("sector")["year"].agg(["min", "max", "count"]).reset_index()
    coverage = _view(
        _label_sectors(coverage_source),
        {
            "sector": "Subsector",
            "min": "First year",
            "max": "Last year",
            "count": "Observations",
        },
    )

    return {
        "tab_composition.tex": latex.table(
            composition,
            caption="Subsector composition of the general-government balance, by statistical "
            "regime. Magnitudes are reported inside each regime because the two differ enough "
            "that a pooled mean describes neither.",
            label="composition",
            digits=2,
            column_digits={"N": 0, "Positive": 0, "Negative": 0},
        ),
        "tab_positive.tex": latex.table(
            positive,
            caption="Every year in which the aggregate balance is positive, with its subsector "
            "composition and the offset ratio.",
            label="positive",
            digits=0,
            column_digits={"Offset ratio": 3},
        ),
        "tab_movements.tex": latex.table(
            movements,
            caption="The largest annual movements inside each statistical regime, ranked on the "
            "absolute change scaled by current-year GDP.",
            label="movements",
            digits=0,
            column_digits={"Rank": 0, "Change (\\% GDP)": 2},
            note="Ranking is within a regime rather than across both. Each annual change is "
            "computed inside one source family, so the changes are sound, but ordering "
            "historical against modern episodes by size would compare two methodologies. 1995 "
            "is excluded: that change straddles the splice in both panels.",
        ),
        "tab_hierarchy.tex": latex.table(
            hierarchy,
            caption="The same episodes, with the subsector accounting for most of each move "
            "split into its own revenue and expenditure changes.",
            label="hierarchy",
            digits=0,
            note="The split is of the named subsector, not of the aggregate. Expenditure enters "
            "the balance negatively, so the final column is minus the expenditure change; it is "
            "that column which adds to the revenue change to give the subsector's balance "
            "change.",
        ),
        "tab_ssfchange.tex": latex.table(
            ssf_change,
            caption="Contributions to the annual change in the Social Security balance. Each "
            "column carries the sign with which the term enters the balance, so the four add to "
            "the change.",
            label="ssfchange",
            digits=0,
            note="A rise in social transfers appears as a negative contribution, because "
            "expenditure reduces the balance. The plain expenditure change would have the "
            "opposite sign and could not be added to the revenue terms.",
        ),
        "tab_primarysigns.tex": latex.table(
            signs,
            caption="Headline against primary balance sign frequencies, over the sector-years "
            "for which interest expenditure is published.",
            label="primarysigns",
            digits=2,
            column_digits={"N": 0, "Headline $<0$": 0, "Primary $>0$": 0},
        ),
        "tab_ssfboundary.tex": latex.table(
            boundary,
            caption="Two accounting boundaries for Social Security, reported side by side. The "
            "columns are never added, netted or reconciled.",
            label="ssfboundary",
            digits=0,
        ),
        "tab_validation.tex": latex.table(
            validation,
            caption="Identity closure and source agreement, in one unit. The two answer "
            "different questions and neither substitutes for the other.",
            label="validation",
            digits=3,
            column_digits={"N": 0},
        ),
        "tab_breakstability.tex": latex.table(
            stability,
            caption="Sensitivity of the detected mean shifts to the two tuning choices, over "
            "twelve specifications per series.",
            label="breakstability",
            digits=2,
            column_digits={"Modal breaks": 0, "Distinct date sets": 0},
        ),
        "tab_coverage.tex": latex.table(
            coverage,
            caption="Coverage of the detailed account panel. The canonical balance panel is "
            "complete; only the detailed components carry the 1996--1999 gap.",
            label="coverage",
            digits=0,
        ),
        "tab_benchmark.tex": latex.table(
            benchmark_view,
            caption="Subsector composition across reporters, ordered by the frequency of a "
            "Social Security surplus. Sign frequencies are shares of the years each reporter "
            "covers completely.",
            label="benchmark",
            digits=3,
            column_digits={
                "N": 0,
                "Surplus years": 0,
                "of which non-SSF $<0$": 0,
                "Mean SSF (\\% GDP)": 2,
            },
            note="The non-Social-Security aggregate is central plus state plus local "
            "government, so federal reporters are treated consistently with unitary ones. "
            "Reporters with fewer than fifteen complete years are excluded, because a "
            "frequency over a handful of years is not comparable with one over thirty.",
        ),
        "tab_benchmarkposition.tex": latex.table(
            position_view,
            caption="Portugal's position in each cross-country distribution. The percentile is "
            "the share of reporters below Portugal's value.",
            label="benchmarkposition",
            digits=3,
            column_digits={"Percentile": 0},
        ),
        "tab_sources.tex": latex.table(
            data.sources,
            caption="Bundled sources, the coverage taken from each, the vintage of the retained "
            "file and the first twelve hexadecimal digits of its SHA-256 digest.",
            label="sources",
        ),
    }


def render_paper_inputs(root: Path) -> list[Path]:
    """Write every generated input the manuscript includes.

    Returns the paths written, so the pipeline can report them and a test can
    check that nothing the prose cites has gone missing.
    """
    data = load(root)
    generated = root / "paper" / "generated"
    generated.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    macros_path = generated / "macros.tex"
    macros_path.write_text(_macro_file(build_macros(data)), encoding="utf-8")
    written.append(macros_path)

    for name, body in _table_files(data).items():
        path = generated / name
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written
