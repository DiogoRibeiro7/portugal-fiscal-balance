"""Repository-level contract tests."""

from __future__ import annotations

from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def test_notebook_pipeline_is_complete_and_ordered() -> None:
    """The visible research pipeline should contain all expected notebook stages."""
    names = [path.name for path in sorted((ROOT / "notebooks").glob("*.ipynb"))]
    assert names == [
        "00_research_protocol.ipynb",
        "01_extract_historical_data.ipynb",
        "02_extract_modern_data.ipynb",
        "03_harmonize_and_validate.ipynb",
        "04_balance_decomposition.ipynb",
        "05_revenue_expenditure.ipynb",
        "06_year_to_year_attribution.ipynb",
        "07_persistence.ipynb",
        "08_structural_breaks.ipynb",
        "09_social_security_mechanisms.ipynb",
        "10_intergovernmental_transfers.ipynb",
        "11_primary_balance.ipynb",
        "12_investment_diagnostic.ipynb",
        "13_debt_reconciliation.ipynb",
        "14_macroeconomic_comovement.ipynb",
        "15_build_report.ipynb",
    ]


def test_notebooks_do_not_reimplement_core_analysis() -> None:
    """Notebooks should expose persisted results, not define reusable analytical functions."""
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert notebooks
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        source = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "code"
        )
        assert "\ndef " not in f"\n{source}", f"Reusable function found in {path.name}"
        assert "\nclass " not in f"\n{source}", f"Reusable class found in {path.name}"

    delegated = {
        "01_extract_historical_data.ipynb",
        "02_extract_modern_data.ipynb",
        "03_harmonize_and_validate.ipynb",
        "15_build_report.ipynb",
    }
    for name in delegated:
        notebook = nbformat.read(ROOT / "notebooks" / name, as_version=4)
        source = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "code"
        )
        assert "portugal_fiscal_balance" in source


def test_report_and_project_do_not_use_precommitted_political_conclusion_labels() -> None:
    """Prevent loaded conclusion labels from becoming part of the analytical contract."""
    forbidden = (
        "artificial surplus",
        "fake surplus",
        "manipulated surplus",
        "social_security_dependent_surplus",
    )
    paths = [ROOT / "README.md", ROOT / "METHODOLOGY.md", ROOT / "report" / "report.tex"]
    paths.extend((ROOT / "src").rglob("*.py"))
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"Forbidden loaded label {phrase!r} found in {path}"


def test_report_is_generated_and_contains_core_analysis_sections() -> None:
    """The final report should expose the main quantitative outputs."""
    report = (ROOT / "report" / "report.tex").read_text(encoding="utf-8")
    expected_headings = [
        r"\section{Long-Run Subsector Decomposition}",
        r"\section{Revenue and Expenditure Dynamics}",
        r"\section{Social Security Funds: Revenue Composition and Internal Systems}",
        r"\section{Primary Balance and Interest}",
        r"\section{Debt and Stock-Flow Adjustment}",
        r"\section{Persistence and Structural Mean Shifts}",
        r"\section{Descriptive Macroeconomic Co-Movement}",
        r"\section{Methodological Limitations}",
    ]
    assert all(heading in report for heading in expected_headings)
