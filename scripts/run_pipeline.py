#!/usr/bin/env python
"""Run the complete deterministic extraction, processing and analysis pipeline."""

# ruff: noqa: E402,I001

from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from portugal_fiscal_balance.analysis.balance import (  # noqa: E402
    compute_balance_metrics,
    summarize_balance_metrics,
)
from portugal_fiscal_balance.analysis.changepoints import (  # noqa: E402
    structural_break_bic_ladder,
    structural_break_sensitivity,
    structural_break_stability,
    structural_break_table,
)
from portugal_fiscal_balance.analysis.comovement import (  # noqa: E402
    build_macro_panel,
    historical_ssf_labour_regression,
    nominal_gdp_comovement_regressions,
)
from portugal_fiscal_balance.analysis.debt import debt_reconciliation_table  # noqa: E402
from portugal_fiscal_balance.analysis.decomposition import (  # noqa: E402
    largest_balance_movements,
    revenue_expenditure_change_decomposition,
    year_to_year_balance_attribution,
)
from portugal_fiscal_balance.analysis import figures  # noqa: E402
from portugal_fiscal_balance.analysis.persistence import (  # noqa: E402
    persistence_by_regime,
    persistence_summary,
    transition_probabilities,
)
from portugal_fiscal_balance.analysis.primary_balance import (  # noqa: E402
    investment_diagnostic,
    primary_balance_sign_summary,
    primary_balance_table,
)
from portugal_fiscal_balance.analysis.social_security import (  # noqa: E402
    social_security_account_metrics,
    social_security_internal_metrics,
    ssf_accounting_boundary_comparison,
    ssf_balance_change_decomposition,
)
from portugal_fiscal_balance.analysis.transfers import transfer_reallocation_sensitivity  # noqa: E402
from portugal_fiscal_balance.io import sha256_file, write_csv, write_json  # noqa: E402
from portugal_fiscal_balance.paths import (  # noqa: E402
    FIGURES,
    INTERIM,
    METRICS,
    PROCESSED,
    RAW,
    TABLES,
    ensure_directories,
)
from portugal_fiscal_balance.processing.harmonize import (  # noqa: E402
    build_methodology_overlap,
    harmonize_account_panel,
    harmonize_balance_panel,
)
from portugal_fiscal_balance.processing.validation import (  # noqa: E402
    compare_modern_balance_sources,
    source_validation_summary,
    validate_accounts,
    validate_balance_panel,
)
from portugal_fiscal_balance.reporting.paper import render_paper_inputs  # noqa: E402
from portugal_fiscal_balance.reporting.render import render_report  # noqa: E402
from portugal_fiscal_balance.sources.banco_portugal import extract_long_series  # noqa: E402
from portugal_fiscal_balance.sources.cfp import (  # noqa: E402
    extract_cfp_annual,
    extract_social_security_detail,
)
from portugal_fiscal_balance.sources.pordata import load_balance_snapshot  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def main() -> None:
    """Execute all deterministic repository stages and persist every key result."""
    ensure_directories()

    historical_path = RAW / "banco_portugal" / "series_longas_2023-12.xlsx"
    pordata_path = RAW / "pordata" / "pordata_2785_balance_by_level_1995_2025.csv"
    cfp_general_path = RAW / "cfp" / "cfp_sec2010_annual_general_government_2026-04-15.xlsx"
    cfp_subsector_path = RAW / "cfp" / "cfp_sec2010_annual_subsectors_2026-04-15.xlsx"
    cfp_ss_path = RAW / "cfp" / "cfp_rel_04_2026_social_security_underlying_data.xlsx"

    # 1. Source extraction.
    historical = extract_long_series(historical_path)
    modern_balance = load_balance_snapshot(pordata_path)
    cfp = extract_cfp_annual(cfp_general_path, cfp_subsector_path)
    ss_systems, ss_detail = extract_social_security_detail(cfp_ss_path)

    write_csv(historical.balances, INTERIM / "historical_balances_1977_1995.csv")
    write_csv(historical.accounts, INTERIM / "historical_accounts_1977_1995.csv")
    write_csv(historical.transfers, INTERIM / "historical_intragov_transfers_1977_1995.csv")
    write_csv(historical.macro, INTERIM / "historical_macro_1977_1995.csv")
    write_csv(modern_balance, INTERIM / "modern_pordata_balances_1995_2025.csv")
    write_csv(cfp.general_government, INTERIM / "cfp_general_government_1995_2025.csv")
    write_csv(cfp.subsectors, INTERIM / "cfp_subsectors_2000_2025.csv")
    write_csv(cfp.accounts, INTERIM / "cfp_accounts_1995_2025.csv")
    write_csv(cfp.debt, INTERIM / "cfp_debt_and_sfa_1995_2025.csv")
    write_csv(ss_systems, INTERIM / "social_security_system_balances_2019_2025.csv")
    write_csv(ss_detail, INTERIM / "social_security_detail_2024_2025.csv")

    source_comparison = compare_modern_balance_sources(
        modern_balance, cfp.general_government, cfp.subsectors
    )
    overlap = build_methodology_overlap(historical.balances, modern_balance)
    write_csv(source_comparison, INTERIM / "modern_source_comparison.csv")
    write_csv(overlap, INTERIM / "methodology_overlap_1995.csv")

    # 2. Canonical processed datasets.
    balance_panel = harmonize_balance_panel(
        historical.balances,
        modern_balance,
        cfp.general_government[["year", "nominal_gdp_m_eur"]],
    )
    account_panel = harmonize_account_panel(historical.accounts, cfp.accounts)
    macro_panel = build_macro_panel(balance_panel, historical.macro)
    write_csv(balance_panel, PROCESSED / "fiscal_balances_1977_2025.csv")
    write_csv(account_panel, PROCESSED / "subsector_accounts_1977_2025.csv")
    write_csv(macro_panel, PROCESSED / "macro_panel_1977_2025.csv")

    # 3. Validation.
    balance_validation = validate_balance_panel(balance_panel)
    account_validation = validate_accounts(account_panel)
    write_csv(account_validation, TABLES / "account_identity_checks.csv")

    # 4. Balance decomposition and dynamics.
    balance_metrics = compute_balance_metrics(balance_panel)
    balance_summary = summarize_balance_metrics(balance_metrics)
    changes = year_to_year_balance_attribution(balance_panel)
    revenue_expenditure_changes = revenue_expenditure_change_decomposition(account_panel)
    persistence = persistence_summary(balance_panel)
    regime_persistence = persistence_by_regime(balance_panel)
    transitions = transition_probabilities(balance_panel)
    breaks = structural_break_table(balance_panel)
    break_ladder = structural_break_bic_ladder(balance_panel)
    break_grid = structural_break_sensitivity(balance_panel)
    break_stability = structural_break_stability(break_grid)
    movements = largest_balance_movements(changes, revenue_expenditure_changes)
    write_csv(balance_metrics, PROCESSED / "annual_balance_metrics_1977_2025.csv")
    write_csv(changes, TABLES / "balance_change_attribution.csv")
    write_csv(revenue_expenditure_changes, TABLES / "revenue_expenditure_change_decomposition.csv")
    write_csv(movements, TABLES / "largest_balance_movements.csv")
    write_csv(persistence, TABLES / "persistence_summary.csv")
    write_csv(regime_persistence, TABLES / "persistence_by_regime.csv")
    write_csv(transitions, TABLES / "transition_probabilities.csv")
    write_csv(breaks, TABLES / "structural_breaks.csv")
    write_csv(break_ladder, TABLES / "structural_break_bic_ladder.csv")
    write_csv(break_grid, TABLES / "structural_break_sensitivity.csv")
    write_csv(break_stability, TABLES / "structural_break_stability.csv")

    # 5. Mechanism diagnostics.
    primary = primary_balance_table(account_panel)
    primary_signs = primary_balance_sign_summary(primary)
    investment = investment_diagnostic(account_panel)
    debt = debt_reconciliation_table(cfp.debt)
    ss_accounts = social_security_account_metrics(account_panel)
    ss_system_metrics, ss_detail_metrics = social_security_internal_metrics(ss_systems, ss_detail)
    ss_boundary = ssf_accounting_boundary_comparison(balance_panel, ss_systems)
    ss_change = ssf_balance_change_decomposition(account_panel)
    transfer_sensitivity = transfer_reallocation_sensitivity(historical.accounts, historical.transfers)
    nominal_comovement = nominal_gdp_comovement_regressions(macro_panel)
    labour_comovement = historical_ssf_labour_regression(macro_panel)
    validation_summary = source_validation_summary(
        balance_panel=balance_panel,
        account_checks=account_validation,
        debt=debt,
        source_comparison=source_comparison,
        overlap=overlap,
    )

    write_csv(primary, TABLES / "primary_balance_and_interest.csv")
    write_csv(primary_signs, TABLES / "primary_balance_sign_summary.csv")
    write_csv(investment, TABLES / "investment_diagnostic.csv")
    write_csv(debt, TABLES / "debt_stock_flow_reconciliation.csv")
    write_csv(ss_accounts, TABLES / "social_security_account_metrics.csv")
    write_csv(ss_system_metrics, TABLES / "social_security_system_metrics_2019_2025.csv")
    write_csv(ss_detail_metrics, TABLES / "social_security_detail_metrics_2024_2025.csv")
    write_csv(ss_boundary, TABLES / "ssf_accounting_boundary_comparison.csv")
    write_csv(ss_change, TABLES / "ssf_balance_change_decomposition.csv")
    write_csv(transfer_sensitivity, TABLES / "historical_transfer_reallocation_sensitivity.csv")
    write_csv(nominal_comovement, TABLES / "nominal_gdp_balance_comovement.csv")
    write_csv(labour_comovement, TABLES / "historical_ssf_labour_comovement.csv")
    write_csv(validation_summary, TABLES / "source_validation_summary.csv")

    # 6. Compact tables used directly by the report.
    recent = balance_metrics.loc[balance_metrics["year"].between(2010, 2025), [
        "year",
        "general_government_balance_m_eur",
        "central_government_balance_m_eur",
        "regional_local_balance_m_eur",
        "social_security_balance_m_eur",
        "non_ssf_balance_m_eur",
        "ssf_offset_ratio",
        "positive_aggregate_with_negative_non_ssf_balance",
    ]]
    write_csv(recent, TABLES / "recent_balance_decomposition_2010_2025.csv")

    # 7. Metrics and reproducibility metadata.
    analysis_diagnostics = {
        "balance_validation": balance_validation,
        "balance_summary": balance_summary,
        "max_abs_account_identity_error_m_eur": float(account_validation["identity_error_m_eur"].abs().max()),
        "n_account_observations": int(len(account_panel)),
        "n_subsector_account_gap_years_1996_1999": 4,
        "max_abs_debt_reconciliation_error_m_eur": float(debt["reconciliation_error_m_eur"].abs().max()),
    }
    write_json(analysis_diagnostics, METRICS / "analysis_summary.json")
    raw_hashes = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in sorted(RAW.rglob("*"))
        if path.is_file()
    }
    write_json(raw_hashes, METRICS / "raw_file_sha256.json")

    # 8. Figures. The notebooks display these same builders inline.
    #
    # The two attribution windows are drawn separately and stop either side of
    # 1995. A single panel spanning the splice would place a vintage revision
    # among the economic movements and give it the same visual weight.
    persisted_figures = {
        "01_long_run_balances.png": figures.balances_by_subsector(balance_metrics),
        "02_ssf_offset_ratio.png": figures.offset_ratio(balance_metrics),
        "03_balance_change_attribution.png": figures.balance_change_attribution(
            changes, start_year=1996, end_year=2025
        ),
        "04_central_revenue_expenditure.png": figures.revenue_expenditure(
            account_panel, "central_government"
        ),
        "05_ssf_contribution_share.png": figures.social_security_contribution_share(ss_accounts),
        "06_central_primary_balance.png": figures.primary_vs_headline(
            primary, "central_government"
        ),
        "07_general_government_debt.png": figures.debt_and_stock_flow(debt),
        "08_subsector_contributions.png": figures.subsector_contributions(balance_metrics),
        "09_balance_sign_states.png": figures.balance_sign_states(balance_panel),
        "10_account_coverage.png": figures.account_coverage(account_panel),
        "11_attribution_historical.png": figures.balance_change_attribution(
            changes, start_year=1978, end_year=1994
        ),
        "12_gg_revenue_expenditure_changes.png": figures.revenue_expenditure_changes(
            revenue_expenditure_changes, "general_government", start_year=2001, end_year=2025
        ),
        "13_ssf_budget_systems.png": figures.social_security_systems(ss_system_metrics),
        "14_ssf_accounting_boundary.png": figures.ssf_accounting_boundary(ss_boundary),
        "15_modern_source_differences.png": figures.modern_source_differences(source_comparison),
        "16_ssf_balance_change_decomposition.png": figures.ssf_balance_change_decomposition(
            ss_change, start_year=2001, end_year=int(ss_change["year"].max())
        ),
    }
    for name, figure in persisted_figures.items():
        figures.save_figure(figure, FIGURES / name)

    # 9. Report generated only from persisted results, then the manuscript's
    #    generated inputs. The report is generated end to end; the manuscript has
    #    authored prose, so only its tables and its numeric macros come from here.
    render_report(ROOT)
    paper_inputs = render_paper_inputs(ROOT)

    print("Pipeline complete")
    print(f"Balance observations: {len(balance_panel)}")
    print(f"Account observations: {len(account_panel)}")
    print(f"Positive aggregate balance years: {balance_summary['positive_aggregate_balance_years']}")
    print(f"Report: {ROOT / 'report' / 'report.tex'}")
    print(f"Paper generated inputs: {len(paper_inputs)} files in paper/generated/")


if __name__ == "__main__":
    main()
