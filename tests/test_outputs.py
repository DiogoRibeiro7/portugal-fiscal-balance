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
