"""Regression tests for the fully built research pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
METRICS = ROOT / "outputs" / "metrics"


def _read_csv(relative: Path) -> pd.DataFrame:
    """Read a generated CSV and fail clearly if the pipeline did not create it."""
    path = ROOT / relative
    assert path.exists(), f"Expected generated file does not exist: {path}"
    return pd.read_csv(path)


def test_balance_panel_has_complete_1977_2025_coverage() -> None:
    """The canonical annual balance panel must contain exactly 1977--2025."""
    panel = _read_csv(Path("data/processed/fiscal_balances_1977_2025.csv"))
    assert panel["year"].tolist() == list(range(1977, 2026))
    assert len(panel) == 49
    assert not panel[
        [
            "general_government_balance_m_eur",
            "central_government_balance_m_eur",
            "regional_local_balance_m_eur",
            "social_security_balance_m_eur",
        ]
    ].isna().any().any()


def test_balance_identity_closes_within_rounding_tolerance() -> None:
    """General Government must equal the sum of the three canonical subsectors."""
    panel = _read_csv(Path("data/processed/fiscal_balances_1977_2025.csv"))
    assert float(panel["closure_error_m_eur"].abs().max()) <= 2.0
    assert bool(panel["closure_within_tolerance"].all())


def test_2025_balance_decomposition_matches_persisted_canonical_values() -> None:
    """Guard the most recent canonical decomposition against accidental parser drift."""
    panel = _read_csv(Path("data/processed/annual_balance_metrics_1977_2025.csv"))
    row = panel.loc[panel["year"].eq(2025)].iloc[0]
    assert row["general_government_balance_m_eur"] == 2059.0
    assert row["central_government_balance_m_eur"] == -5636.0
    assert row["regional_local_balance_m_eur"] == 630.0
    assert row["social_security_balance_m_eur"] == 7065.0
    assert row["non_ssf_balance_m_eur"] == -5006.0
    assert np.isclose(row["ssf_offset_ratio"], 7065.0 / 5006.0)


def test_positive_aggregate_balance_years_are_reproducible() -> None:
    """The positive-balance year set is a calculated output, not a hard-coded narrative."""
    annual = _read_csv(Path("data/processed/annual_balance_metrics_1977_2025.csv"))
    years = annual.loc[annual["aggregate_balance_positive"], "year"].tolist()
    assert years == [2019, 2023, 2024, 2025]
    selected = annual.loc[annual["aggregate_balance_positive"]]
    assert selected["positive_aggregate_with_negative_non_ssf_balance"].all()
    assert selected["ssf_exceeds_aggregate_balance"].all()


def test_detailed_accounts_preserve_source_gap_without_imputation() -> None:
    """Detailed subsector accounts must not fabricate 1996--1999 observations."""
    accounts = _read_csv(Path("data/processed/subsector_accounts_1977_2025.csv"))
    counts = accounts.groupby("sector")["year"].count().to_dict()
    assert counts == {
        "central_government": 45,
        "general_government": 49,
        "regional_local_government": 45,
        "social_security_funds": 45,
    }
    subsectors = accounts.loc[accounts["sector"].ne("general_government")]
    assert subsectors.loc[subsectors["year"].between(1996, 1999)].empty


def test_accounting_identity_is_exact_up_to_numeric_precision() -> None:
    """Revenue minus expenditure must reproduce B.9 wherever both are available."""
    checks = _read_csv(Path("outputs/tables/account_identity_checks.csv"))
    finite = checks["identity_error_m_eur"].dropna()
    assert len(finite) > 0
    assert float(finite.abs().max()) < 1e-6


def test_methodology_overlap_keeps_both_1995_versions() -> None:
    """The known 1995 source overlap must remain visible rather than silently spliced."""
    overlap = _read_csv(Path("data/interim/methodology_overlap_1995.csv"))
    assert len(overlap) == 4
    assert set(overlap["metric"]) == {
        "general_government_balance_m_eur",
        "central_government_balance_m_eur",
        "regional_local_balance_m_eur",
        "social_security_balance_m_eur",
    }
    assert overlap["historical_1995_m_eur"].notna().all()
    assert overlap["modern_1995_m_eur"].notna().all()
    assert overlap["difference_m_eur"].abs().gt(0).all()


def test_balance_change_attribution_closes() -> None:
    """Annual General Government balance changes must equal subsector changes."""
    attribution = _read_csv(Path("outputs/tables/balance_change_attribution.csv"))
    assert float(attribution["change_closure_error_m_eur"].abs().max()) <= 2.0


def test_gdp_scaled_attribution_decomposes_as_exactly_as_the_level_version() -> None:
    """Sharing one denominator means the scaling adds no error of its own.

    The scaled residual is not zero, because it inherits the level closure error
    left by the sources' one-million-euro rounding. What must hold is that it is
    exactly that error rescaled, and nothing more.

    The tolerance is set by how the artefact is persisted, not by the arithmetic:
    the pipeline writes CSVs at ten significant digits, so a recomputation from the
    file agrees to about 1e-10 rather than to machine precision.
    """
    attribution = _read_csv(Path("outputs/tables/balance_change_attribution.csv"))
    parts = (
        attribution["central_change_pct_gdp"]
        + attribution["regional_local_change_pct_gdp"]
        + attribution["ssf_change_pct_gdp"]
    )
    scaled_residual = attribution["aggregate_change_pct_gdp"] - parts
    inherited = (
        100.0
        * attribution["change_closure_error_m_eur"]
        / attribution["nominal_gdp_m_eur"]
    )
    assert float((scaled_residual - inherited).abs().max()) < 1e-9
    # And the inherited error stays at the rounding scale it comes from.
    assert float(scaled_residual.abs().max()) < 1e-3


def test_largest_movements_rank_within_each_regime_not_across_them() -> None:
    """Ranking across the splice would order two methodologies by size."""
    movements = _read_csv(Path("outputs/tables/largest_balance_movements.csv"))
    assert set(movements["regime"]) == {"1977-1994_historical", "1995-2025_modern"}
    assert 1995 not in movements["year"].tolist()

    for regime, group in movements.groupby("regime"):
        ordered = group.sort_values("rank_in_regime")
        assert ordered["rank_in_regime"].tolist() == list(range(1, len(ordered) + 1))
        # Ranking is on absolute size, so magnitudes must fall down the ranking.
        magnitudes = ordered["aggregate_change_pct_gdp"].abs().tolist()
        assert magnitudes == sorted(magnitudes, reverse=True), f"Bad ordering in {regime}"
        # Every year must belong to the regime it is ranked in.
        if regime == "1977-1994_historical":
            assert ordered["year"].between(1977, 1994).all()
        else:
            assert ordered["year"].between(1995, 2025).all()

    directions = movements["direction"]
    assert (movements.loc[directions.eq("improvement"), "aggregate_change_pct_gdp"] > 0).all()
    assert (movements.loc[directions.eq("deterioration"), "aggregate_change_pct_gdp"] < 0).all()

    # Ranking on the GDP scale must actually change the selection, otherwise the
    # scaling would be decorative.
    attribution = _read_csv(Path("outputs/tables/balance_change_attribution.csv"))
    nominal_top = set(
        attribution.reindex(
            attribution["aggregate_change_m_eur"].abs().sort_values(ascending=False).index
        )
        .head(len(movements))["year"]
        .tolist()
    )
    assert set(movements["year"]) != nominal_top


def test_movement_attribution_is_hierarchical_not_parallel() -> None:
    """The revenue/expenditure split must describe the subsector it sits beside.

    Reporting aggregate revenue and expenditure next to a subsector attribution
    invites the reader to connect quantities that describe different entities.
    """
    movements = _read_csv(Path("outputs/tables/largest_balance_movements.csv"))
    changes = _read_csv(Path("outputs/tables/revenue_expenditure_change_decomposition.csv"))
    labels = {
        "Central Government": "central_government",
        "Regional and Local": "regional_local_government",
        "Social Security Funds": "social_security_funds",
    }
    for row in movements.itertuples(index=False):
        source = changes.loc[
            changes["sector"].eq(labels[row.dominant_subsector]) & changes["year"].eq(row.year)
        ]
        assert len(source) == 1, f"No account row for {row.dominant_subsector} in {row.year}"
        assert np.isclose(row.dominant_revenue_change_m_eur, source["revenue_change_m_eur"].iloc[0])
        assert np.isclose(
            row.dominant_expenditure_change_m_eur, source["expenditure_change_m_eur"].iloc[0]
        )
        # The expenditure contribution carries the sign with which it enters the
        # balance, which is the opposite of the raw change.
        assert np.isclose(
            row.dominant_expenditure_contribution_m_eur, -row.dominant_expenditure_change_m_eur
        )
    # The two source families measure the same subsector change slightly
    # differently; the residual must stay at the sources' rounding scale.
    assert float(movements["dominant_split_error_m_eur"].abs().max()) < 2.0


def test_component_contributions_close_to_the_balance_change() -> None:
    """The component split must reproduce the balance change it decomposes."""
    frame = _read_csv(Path("outputs/tables/account_component_changes.csv"))
    assert not frame.empty
    assert float(frame["component_closure_error_m_eur"].abs().max()) < 1e-6

    totals = frame.groupby(["sector", "year"]).agg(
        contributions=("contribution_m_eur", "sum"),
        balance_change=("balance_change_m_eur", "first"),
    )
    assert np.allclose(totals["contributions"], totals["balance_change"], atol=1e-6)


def test_each_sector_year_uses_the_finest_component_scheme_it_reports() -> None:
    """Coarsening the modern period to the historical scheme would discard real detail."""
    frame = _read_csv(Path("outputs/tables/account_component_changes.csv"))
    schemes = frame.groupby(["sector", "year"])["component_scheme"].nunique()
    assert (schemes == 1).all(), "A sector-year carries more than one scheme"

    modern = frame.loc[frame["component_scheme"].eq("modern_detailed")]
    historical = frame.loc[frame["component_scheme"].eq("historical_current_capital")]
    assert not modern.empty and not historical.empty
    # The modern scheme resolves the accounts further than the historical one, which
    # is the reason for keeping both rather than forcing a common set.
    assert modern["component"].nunique() > historical["component"].nunique()
    assert (historical["year"] <= 1995).all()
    assert (modern["year"] >= 1995).all()


def test_expenditure_components_contribute_with_the_opposite_sign() -> None:
    """A rise in an expenditure component must reduce the balance."""
    frame = _read_csv(Path("outputs/tables/account_component_changes.csv"))
    revenue = frame.loc[frame["side"].eq("revenue")]
    expenditure = frame.loc[frame["side"].eq("expenditure")]
    assert not revenue.empty and not expenditure.empty
    assert np.allclose(revenue["contribution_m_eur"], revenue["change_m_eur"])
    assert np.allclose(expenditure["contribution_m_eur"], -expenditure["change_m_eur"])


def test_episode_components_describe_the_dominant_subsector() -> None:
    """All three levels of the attribution must refer to one entity."""
    episodes = _read_csv(Path("outputs/tables/episode_component_attribution.csv"))
    movements = _read_csv(Path("outputs/tables/largest_balance_movements.csv"))
    components = _read_csv(Path("outputs/tables/account_component_changes.csv"))
    assert not episodes.empty

    labels = {
        "Central Government": "central_government",
        "Regional and Local": "regional_local_government",
        "Social Security Funds": "social_security_funds",
    }
    keyed = movements.set_index(["regime", "rank_in_regime"])
    for row in episodes.itertuples(index=False):
        episode = keyed.loc[(row.regime, row.rank_in_regime)]
        assert row.year == episode["year"]
        assert row.dominant_subsector == episode["dominant_subsector"]
        # The component figure must come from that subsector's own accounts.
        source = components.loc[
            components["sector"].eq(labels[row.dominant_subsector])
            & components["year"].eq(row.year)
            & components["component"].eq(row.component)
        ]
        assert len(source) == 1
        assert np.isclose(row.contribution_m_eur, source["contribution_m_eur"].iloc[0])

    # Ranked by absolute contribution within each episode.
    for _, group in episodes.groupby(["regime", "rank_in_regime"], sort=False):
        magnitudes = group["contribution_m_eur"].abs().tolist()
        assert magnitudes == sorted(magnitudes, reverse=True)


def test_ssf_balance_change_decomposition_closes_on_contributions() -> None:
    """The four contributions must add to the balance change, signs included."""
    frame = _read_csv(Path("outputs/tables/ssf_balance_change_decomposition.csv"))
    assert not frame.empty
    assert float(frame["balance_identity_error_m_eur"].abs().max()) < 1e-6
    assert float(frame["revenue_split_error_m_eur"].abs().max()) < 1e-6

    detailed = frame.dropna(subset=["other_expenditure_contribution_m_eur"])
    assert len(detailed) > 20, "Expenditure detail is missing for the modern period"
    assert float(detailed["expenditure_split_error_m_eur"].abs().max()) < 1e-6
    assert float(detailed["contribution_closure_error_m_eur"].abs().max()) < 1e-6

    parts = (
        detailed["contributions_contribution_m_eur"]
        + detailed["other_revenue_contribution_m_eur"]
        + detailed["social_transfers_contribution_m_eur"]
        + detailed["other_expenditure_contribution_m_eur"]
    )
    assert np.allclose(parts, detailed["balance_change_m_eur"])


def test_ssf_expenditure_contributions_oppose_their_raw_changes() -> None:
    """A rise in expenditure must appear as a negative contribution to the balance."""
    frame = _read_csv(Path("outputs/tables/ssf_balance_change_decomposition.csv"))
    detailed = frame.dropna(subset=["social_transfers_change_m_eur"])
    assert np.allclose(
        detailed["social_transfers_contribution_m_eur"],
        -detailed["social_transfers_change_m_eur"],
    )
    assert np.allclose(
        detailed["other_expenditure_contribution_m_eur"],
        -detailed["other_expenditure_change_m_eur"],
    )
    # Social transfers grew in most years, so their contribution is mostly negative.
    assert (detailed["social_transfers_contribution_m_eur"] < 0).mean() > 0.5


def test_no_change_is_computed_across_the_subsector_source_gap() -> None:
    """The Social Security decomposition must not bridge 1995 to 2000."""
    frame = _read_csv(Path("outputs/tables/ssf_balance_change_decomposition.csv"))
    assert 2000 not in frame["year"].tolist(), "A change was computed across the gap"
    assert frame.loc[frame["year"].between(1996, 1999)].empty


def test_largest_movements_name_a_contributor_by_label_not_by_column() -> None:
    """The dominant-contributor column feeds the report, so it must be readable."""
    movements = _read_csv(Path("outputs/tables/largest_balance_movements.csv"))
    assert set(movements["dominant_subsector"]) <= {
        "Central Government",
        "Regional and Local",
        "Social Security Funds",
    }
    for row in movements.itertuples(index=False):
        contributions = {
            "Central Government": row.central_change_m_eur,
            "Regional and Local": row.regional_local_change_m_eur,
            "Social Security Funds": row.ssf_change_m_eur,
        }
        expected = max(contributions, key=lambda key: abs(contributions[key]))
        assert row.dominant_subsector == expected, f"Wrong contributor for {row.year}"


def test_revenue_expenditure_change_decomposition_closes() -> None:
    """For adjacent source years, delta balance must equal delta revenue minus delta expenditure."""
    changes = _read_csv(Path("outputs/tables/revenue_expenditure_change_decomposition.csv"))
    error = changes["decomposition_error_m_eur"].dropna()
    assert len(error) > 0
    assert float(error.abs().max()) < 1e-6


def test_persistence_outputs_match_canonical_sign_counts() -> None:
    """Persistence summaries must be derived consistently from the canonical balance panel."""
    summary = _read_csv(Path("outputs/tables/persistence_summary.csv")).set_index("sector")
    assert int(summary.loc["central_government", "positive_years"]) == 0
    assert int(summary.loc["central_government", "negative_years"]) == 49
    assert int(summary.loc["social_security_funds", "positive_years"]) == 43
    assert int(summary.loc["social_security_funds", "negative_years"]) == 6


def test_balance_panel_carries_the_publisher_provisional_flag() -> None:
    """Provisional years must stay identifiable instead of being presented as settled."""
    panel = _read_csv(Path("data/processed/fiscal_balances_1977_2025.csv"))
    assert "vintage_status" in panel.columns
    assert not panel["vintage_status"].isna().any()
    provisional = panel.loc[panel["vintage_status"].eq("provisional"), "year"].tolist()
    assert provisional == [2024, 2025]
    historical = panel.loc[panel["year"].le(1994), "vintage_status"]
    assert (historical == "final").all()


def test_regime_persistence_splits_the_pooled_summary_without_losing_observations() -> None:
    """Every year counted in the pooled summary must appear in exactly one regime."""
    pooled = _read_csv(Path("outputs/tables/persistence_summary.csv")).set_index("sector")
    regime = _read_csv(Path("outputs/tables/persistence_by_regime.csv"))
    assert set(regime["regime"]) == {"1977-1994_historical", "1995-2025_modern"}
    totals = regime.groupby("sector")[["n_years", "positive_years", "negative_years"]].sum()
    for sector in totals.index:
        for column in ("n_years", "positive_years", "negative_years"):
            assert int(totals.loc[sector, column]) == int(pooled.loc[sector, column])


def test_regime_means_straddle_the_pooled_mean_they_replace() -> None:
    """The pooled mean describes neither regime, which is the reason for the split."""
    pooled = _read_csv(Path("outputs/tables/persistence_summary.csv")).set_index("sector")
    regime = _read_csv(Path("outputs/tables/persistence_by_regime.csv"))
    aggregate = regime.loc[regime["sector"].eq("general_government")].set_index("regime")
    historical = float(aggregate.loc["1977-1994_historical", "mean_balance_pct_gdp"])
    modern = float(aggregate.loc["1995-2025_modern", "mean_balance_pct_gdp"])
    combined = float(pooled.loc["general_government", "mean_balance_pct_gdp"])
    assert historical < combined < modern
    assert modern - historical > 2.0


def test_structural_break_sensitivity_covers_the_full_tuning_grid() -> None:
    """Twelve specifications per series, so a date cannot rest on one tuning choice."""
    grid = _read_csv(Path("outputs/tables/structural_break_sensitivity.csv"))
    assert sorted(grid["min_segment"].unique()) == [4, 5, 6, 7]
    assert sorted(grid["max_breaks"].unique()) == [1, 2, 3]
    counts = grid.groupby(["regime", "sector"]).size()
    assert (counts == 12).all()
    assert len(counts) == 8
    assert (grid["n_breaks"] <= grid["max_breaks"]).all()


def test_structural_break_bic_ladder_scores_the_zero_break_model() -> None:
    """A selected break count is only meaningful beside the counts it beat."""
    ladder = _read_csv(Path("outputs/tables/structural_break_bic_ladder.csv"))
    for (regime, sector), group in ladder.groupby(["regime", "sector"]):
        label = f"{regime}/{sector}"
        assert 0 in group["n_breaks"].tolist(), f"No zero-break score for {label}"
        assert int(group["selected"].sum()) == 1, f"Not exactly one selection for {label}"
        assert float(group["delta_bic_vs_best"].min()) == 0.0
        assert (group["delta_bic_vs_best"] >= 0.0).all()
        selected = group.loc[group["selected"]].iloc[0]
        assert float(selected["delta_bic_vs_best"]) == 0.0


def test_structural_break_stability_reports_agreement_shares() -> None:
    """Date stability has to be quantified, not asserted."""
    stability = _read_csv(Path("outputs/tables/structural_break_stability.csv"))
    assert len(stability) == 8
    assert (stability["n_specifications"] == 12).all()
    for column in ("modal_n_breaks_share", "modal_break_years_share"):
        assert (stability[column] > 0.0).all()
        assert (stability[column] <= 1.0).all()
    assert (stability["n_distinct_break_year_sets"] >= 1).all()


def test_structural_breaks_do_not_cross_known_methodology_splice() -> None:
    """Break detection must run separately on the historical and modern regimes."""
    breaks = _read_csv(Path("outputs/tables/structural_breaks.csv"))
    assert len(breaks) == 8
    assert set(breaks["regime"]) == {"1977-1994_historical", "1995-2025_modern"}
    for row in breaks.itertuples(index=False):
        if pd.isna(row.break_years):
            continue
        years = [int(value) for value in str(row.break_years).split(";")]
        if row.regime == "1977-1994_historical":
            assert all(1977 <= year <= 1994 for year in years)
        else:
            assert all(1995 <= year <= 2025 for year in years)


def test_primary_balance_reconstruction_closes() -> None:
    """B.9 plus interest must equal the reconstructed primary balance."""
    primary = _read_csv(Path("outputs/tables/primary_balance_and_interest.csv"))
    assert float(primary["primary_balance_identity_error_m_eur"].abs().max()) < 1e-6


def test_central_primary_balance_is_positive_in_years_the_headline_never_is() -> None:
    """Guard the nuance: a permanently negative B.9 is not a permanent primary deficit."""
    signs = _read_csv(Path("outputs/tables/primary_balance_sign_summary.csv")).set_index("sector")
    central = signs.loc["central_government"]
    assert int(central["n_years"]) == 45
    assert int(central["headline_negative_years"]) == 45
    assert int(central["headline_positive_years"]) == 0
    assert int(central["primary_positive_years"]) == 15
    years = [int(value) for value in str(central["primary_positive_year_list"]).split(";")]
    assert len(years) == 15
    assert years == sorted(years)
    # The positive-primary years are not confined to the recent period, which is
    # what makes the distinction a long-run result rather than a recent artefact.
    assert min(years) < 1995
    assert max(years) == 2025


def test_primary_balance_sign_summary_agrees_with_the_underlying_panel() -> None:
    """The summary must be derived from the persisted panel, not maintained beside it."""
    primary = _read_csv(Path("outputs/tables/primary_balance_and_interest.csv"))
    signs = _read_csv(Path("outputs/tables/primary_balance_sign_summary.csv")).set_index("sector")
    for sector, group in primary.groupby("sector"):
        row = signs.loc[sector]
        assert int(row["n_years"]) == len(group)
        assert int(row["primary_positive_years"]) == int(
            (group["primary_balance_recomputed_m_eur"] > 0).sum()
        )
        assert int(row["headline_negative_years"]) == int((group["balance_m_eur"] < 0).sum())


def test_debt_stock_flow_reconciliation_closes() -> None:
    """The modern debt change must reconcile with B.9 and the stock-flow adjustment."""
    debt = _read_csv(Path("outputs/tables/debt_stock_flow_reconciliation.csv"))
    assert float(debt["reconciliation_error_m_eur"].abs().max()) < 1e-6


def test_social_security_internal_system_values_are_preserved() -> None:
    """Guard the separately sourced CFP Social Security budget-system extraction."""
    systems = _read_csv(Path("outputs/tables/social_security_system_metrics_2019_2025.csv"))
    row = systems.loc[systems["year"].eq(2025)].iloc[0]
    assert row["previdential_system_balance_m_eur"] == 6712
    assert row["citizenship_system_balance_m_eur"] == -55
    assert row["special_regimes_balance_m_eur"] == 0


def test_the_two_social_security_boundaries_never_coincide() -> None:
    """The gap is the finding: the two objects must not be used interchangeably."""
    boundary = _read_csv(Path("outputs/tables/ssf_accounting_boundary_comparison.csv"))
    assert not boundary.empty
    assert boundary["boundary_difference_m_eur"].notna().all()
    assert (boundary["boundary_difference_m_eur"].abs() > 0).all()
    row = boundary.loc[boundary["year"].eq(2025)].iloc[0]
    assert row["esa2010_ssf_balance_m_eur"] == 7065
    assert row["budget_system_total_m_eur"] == 6657
    assert row["boundary_difference_m_eur"] == 408
    # Small relative to the balances, which is exactly why it is easy to miss.
    assert (boundary["boundary_difference_share_esa_balance"].abs() < 0.15).all()


def test_source_validation_summary_separates_identity_from_agreement() -> None:
    """Both kinds of check must be present, because closure does not imply agreement."""
    summary = _read_csv(Path("outputs/tables/source_validation_summary.csv"))
    kinds = set(summary["check"])
    assert {"Accounting identity", "Source agreement", "Vintage revision"} <= kinds

    identities = summary.loc[summary["check"].eq("Accounting identity")]
    assert len(identities) == 3
    assert float(identities["max_abs_difference_m_eur"].max()) <= 2.0

    agreements = summary.loc[summary["check"].eq("Source agreement")]
    assert len(agreements) == 4
    worst = float(agreements["max_abs_difference_m_eur"].max())
    # The point of the table: two published sources disagree by far more than any
    # identity residual, so identity closure cannot stand in for agreement.
    assert worst > 10.0
    assert worst > float(identities["max_abs_difference_m_eur"].max())
    assert (summary["n_observations"] > 0).all()


def test_european_panel_closes_the_identity_for_every_reporter() -> None:
    """A benchmark built on an open identity would compare incomparable aggregates."""
    panel = _read_csv(Path("data/processed/european_subsector_panel_1995_2025.csv"))
    assert panel["country"].nunique() > 20
    closure = panel["closure_error_mio_nac"].abs().dropna()
    assert len(closure) > 800

    # The tolerance is publication precision, tested in absolute terms. A relative
    # test is the wrong instrument here twice over: the aggregate is near zero by
    # construction in the years this analysis is about, and several reporters have
    # components of only a few million national currency units, so ordinary rounding
    # looks like a large relative error in both cases.
    assert float(closure.max()) <= 2.0, "Residual exceeds the coarsest publication rounding"
    # Most reporters publish to one decimal, where four rounded components can differ
    # by at most about 0.2.
    assert float((closure <= 0.2).mean()) > 0.95


def test_state_government_is_included_in_the_non_ssf_aggregate() -> None:
    """Omitting the state tier would leave federal reporters' identity open."""
    panel = _read_csv(Path("data/processed/european_subsector_panel_1995_2025.csv"))
    federal = panel.loc[panel["has_state_tier"]]
    assert not federal.empty, "No reporter with a state tier was found"
    assert federal["country"].nunique() >= 4
    # With the state tier included these reporters close to publication rounding.
    assert float(federal["closure_error_mio_nac"].abs().max()) <= 2.0

    # And the tier is materially large, so omitting it would be a real error rather
    # than a rounding one. This is what makes its inclusion a substantive choice.
    assert float(federal["state_government_mio_nac"].abs().max()) > 1000.0
    # Portugal has no state tier, which is why its aggregate is central plus local.
    portugal = panel.loc[panel["country"].eq("PT")]
    assert not portugal["has_state_tier"].any()


def test_european_panel_reproduces_the_domestic_portuguese_series() -> None:
    """Eurostat compiles Portugal independently, so agreement checks the extraction."""
    panel = _read_csv(Path("data/processed/european_subsector_panel_1995_2025.csv"))
    domestic = _read_csv(Path("data/processed/fiscal_balances_1977_2025.csv"))
    merged = panel.loc[panel["country"].eq("PT")].merge(domestic, on="year", how="inner")
    assert len(merged) >= 30
    for external, internal in (
        ("general_government_mio_nac", "general_government_balance_m_eur"),
        ("social_security_mio_nac", "social_security_balance_m_eur"),
    ):
        gap = (merged[external] - merged[internal]).abs()
        assert float(gap.max()) < 1.0, f"{external} disagrees with {internal}"


def test_offset_ratio_is_not_computed_on_a_rounding_scale_denominator() -> None:
    """A near-zero denominator would manufacture a large ratio from rounding."""
    panel = _read_csv(Path("data/processed/european_subsector_panel_1995_2025.csv"))
    defined = panel.dropna(subset=["offset_ratio"])
    assert not defined.empty
    assert (defined["non_ssf_pct_gdp"].abs() >= 0.5).all()
    assert (defined["non_ssf_mio_nac"] < 0).all()
    assert (defined["social_security_mio_nac"] > 0).all()
    assert (defined["offset_ratio"] > 0).all()


def test_benchmark_summary_excludes_aggregates_and_short_reporters() -> None:
    """The euro area is not a peer of its members, and a short panel is not comparable."""
    summary = _read_csv(Path("outputs/tables/european_benchmark_summary.csv"))
    assert not summary.empty
    aggregates = {"EA", "EA19", "EA20", "EA21", "EU", "EU27_2020", "EU28"}
    assert not (set(summary["country"]) & aggregates)
    assert (summary["n_years"] >= 15).all()
    assert "PT" in set(summary["country"])
    for column in ("share_central_negative", "share_ssf_positive", "share_aggregate_positive"):
        assert summary[column].between(0.0, 1.0).all()
    # The structural count cannot exceed the number of surplus years it counts within.
    assert (
        summary["n_aggregate_positive_with_negative_non_ssf"] <= summary["n_aggregate_positive"]
    ).all()


def test_benchmark_position_locates_portugal_without_asserting_it() -> None:
    """The percentile must be derived from the summary, not stated beside it."""
    summary = _read_csv(Path("outputs/tables/european_benchmark_summary.csv"))
    position = _read_csv(Path("outputs/tables/european_benchmark_position.csv"))
    assert not position.empty
    assert position["percentile"].between(0.0, 100.0).all()

    portugal = summary.loc[summary["country"].eq("PT")].iloc[0]
    checks = {
        "Share of years with a Social Security surplus": "share_ssf_positive",
        "Mean Social Security balance (% GDP)": "mean_ssf_pct_gdp",
    }
    for metric, column in checks.items():
        row = position.loc[position["metric"].eq(metric)].iloc[0]
        assert np.isclose(row["country_value"], portugal[column])
        expected = 100.0 * (summary[column] < portugal[column]).mean()
        assert np.isclose(row["percentile"], expected)
        assert row["cross_country_min"] <= row["country_value"] <= row["cross_country_max"]


def test_analysis_summary_records_validation_diagnostics() -> None:
    """Machine-readable pipeline diagnostics must be persisted for independent checking."""
    path = METRICS / "analysis_summary.json"
    with path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["balance_validation"]["n_years"] == 49
    assert summary["n_account_observations"] == 184
    assert summary["balance_validation"]["max_abs_closure_error_m_eur"] <= 2.0
    assert summary["max_abs_debt_reconciliation_error_m_eur"] < 1e-6


def test_raw_file_hash_manifest_is_nonempty() -> None:
    """Every bundled source should have a reproducibility hash manifest."""
    path = METRICS / "raw_file_sha256.json"
    with path.open("r", encoding="utf-8") as handle:
        hashes = json.load(handle)
    assert len(hashes) >= 5
    assert all(len(value) == 64 for value in hashes.values())


def test_contribution_decomposition_is_exact_on_both_levels() -> None:
    """Both nested product decompositions must close by construction."""
    frame = _read_csv(Path("outputs/tables/contribution_change_decomposition.csv"))
    assert not frame.empty
    assert float(frame["contributions_closure_error_m_eur"].abs().max()) < 1e-6
    assert float(frame["wage_bill_closure_error_m_eur"].abs().max()) < 1e-6

    contributions = (
        frame["from_wage_bill_m_eur"]
        + frame["from_ratio_m_eur"]
        + frame["wage_bill_ratio_interaction_m_eur"]
    )
    assert np.allclose(contributions, frame["contributions_change_m_eur"])

    wage_bill = (
        frame["from_employment_m_eur"]
        + frame["from_average_wage_m_eur"]
        + frame["employment_wage_interaction_m_eur"]
    )
    assert np.allclose(wage_bill, frame["wage_bill_change_m_eur"])


def test_no_contribution_change_bridges_the_subsector_source_gap() -> None:
    """Differencing 1995 against 2000 would present five years of growth as one.

    This is not hypothetical: bridging the gap moves the wage-bill regression slope
    from 0.25 to 0.13 and its fit from 0.93 to 0.40, on one contaminated observation.
    """
    frame = _read_csv(Path("outputs/tables/contribution_change_decomposition.csv"))
    years = frame["year"].tolist()
    assert 2000 not in years, "A five-year change was computed as annual"
    assert years == list(range(min(years), max(years) + 1)), "Years are not contiguous"


def test_contribution_base_uses_wages_rather_than_total_compensation() -> None:
    """Compensation of employees contains employers' contributions.

    Using it as the base would place part of the numerator inside the denominator and
    depress the effective ratio, so the panel must carry the narrower measure.
    """
    panel = _read_csv(Path("data/processed/contribution_base_panel_1995_2025.csv"))
    assert "wage_bill_m_eur" in panel.columns
    assert (panel["wage_bill_m_eur"] < panel["compensation_of_employees_m_eur"]).all()
    implied = panel["contributions_m_eur"] / panel["wage_bill_m_eur"]
    assert np.allclose(implied, panel["contributions_to_wage_bill_ratio"])
    # An effective ratio, not a statutory rate: it sits well below the headline levy.
    assert panel["contributions_to_wage_bill_ratio"].between(0.10, 0.40).all()


def test_wage_bill_regression_recovers_the_effective_ratio() -> None:
    """The slope should land near the ratio the accounting implies."""
    regression = _read_csv(Path("outputs/tables/contribution_wage_bill_regression.csv"))
    assert len(regression) == 1
    row = regression.iloc[0]
    assert row["n"] >= 20
    assert abs(row["coef_minus_mean_ratio"]) < 0.10
    # Comfortably tighter than the nominal-GDP specification it replaces, whose fits
    # span 0.07 to 0.18.
    assert row["r_squared"] > 0.5
    assert row["wage_bill_pvalue_hac"] < 0.05


def test_state_tier_is_required_of_countries_that_operate_one() -> None:
    """A missing S.1312 is benign only where the tier does not exist.

    For a country that does operate one, an absent observation is an unknown value,
    and summing it as zero while still calling the year complete would understate
    that country's non-Social-Security deficit without any signal.
    """
    panel = _read_csv(Path("data/processed/european_subsector_panel_1995_2025.csv"))
    assert "state_tier_expected" in panel.columns

    expected = panel.loc[panel["state_tier_expected"]]
    assert not expected.empty, "No reporter is recorded as operating a state tier"
    assert set(expected["country"]) >= {"DE", "ES", "AT", "BE"}

    unresolved = expected.loc[expected["state_government_mio_nac"].isna() & expected["complete"]]
    assert unresolved.empty, (
        "Country-years marked complete while a state tier they operate is missing: "
        f"{unresolved[['country', 'year']].to_dict('records')}"
    )
    # Portugal has no such tier, so its years must not be held to the requirement.
    portugal = panel.loc[panel["country"].eq("PT")]
    assert not portugal["state_tier_expected"].any()
    assert portugal["complete"].all()


def test_offset_position_survives_the_denominator_floor() -> None:
    """The floor is a researcher's choice, so the conclusion must not hinge on it."""
    sensitivity = _read_csv(Path("outputs/tables/european_offset_floor_sensitivity.csv"))
    assert len(sensitivity) >= 4
    assert sensitivity["floor_pct_gdp"].is_monotonic_increasing
    # A higher floor discards more country-years, by construction.
    assert sensitivity["n_defined_country_years"].is_monotonic_decreasing
    # Portugal stays mid-distribution throughout; a swing would mean the "ordinary"
    # reading was an artefact of where the floor was set.
    spread = sensitivity["percentile"].max() - sensitivity["percentile"].min()
    assert spread < 20.0, f"Portugal's percentile moves {spread:.0f} points with the floor"
    assert sensitivity["percentile"].between(25.0, 75.0).all()


def test_surplus_composition_agrees_under_both_weightings() -> None:
    """Pooling by country-year lets long surplus runs dominate; check the alternative."""
    composition = _read_csv(Path("outputs/tables/european_surplus_composition.csv"))
    assert len(composition) == 1
    row = composition.iloc[0]
    assert row["pooled_offsetting_years"] < row["pooled_surplus_years"]
    # The two weightings answer different questions and need not agree exactly, but a
    # large divergence would mean the pooled figure is driven by a few long runs.
    assert abs(row["pooled_share"] - row["country_weighted_median"]) < 0.15
    assert row["country_weighted_lower_quartile"] <= row["country_weighted_median"]
    assert row["country_weighted_median"] <= row["country_weighted_upper_quartile"]
    # Portugal is at the top of the distribution on both readings.
    assert row["country_share"] == 1.0
    assert row["country_percentile"] > 90.0
