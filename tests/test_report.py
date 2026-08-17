"""Structural tests for the generated LaTeX report.

The report restates persisted results, so these tests check that the restatement
stays wired to the artefacts: every included figure exists, every cross-reference
resolves, the headline numbers agree with the panels, and no raw column
identifier leaks into the prose.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report" / "report.tex"


def _report() -> str:
    """Read the generated report, failing clearly if the pipeline has not run."""
    assert REPORT.exists(), f"Expected generated report does not exist: {REPORT}"
    return REPORT.read_text(encoding="utf-8")


def test_every_included_figure_exists() -> None:
    """A figure referenced by the report must be present in outputs/figures."""
    included = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", _report())
    assert included, "The report includes no figures"
    missing = [name for name in included if not (ROOT / "outputs" / "figures" / name).exists()]
    assert not missing, f"Report references figures that do not exist: {missing}"


def test_every_persisted_figure_is_used() -> None:
    """A figure the pipeline writes should be shown somewhere in the report."""
    included = set(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", _report()))
    persisted = {path.name for path in (ROOT / "outputs" / "figures").glob("*.png")}
    assert persisted, "The pipeline wrote no figures"
    assert not persisted - included, f"Persisted figures never shown: {sorted(persisted - included)}"


def test_every_cross_reference_resolves() -> None:
    """Table and figure references must point at labels that exist."""
    report = _report()
    labels = set(re.findall(r"\\label\{([^}]+)\}", report))
    references = set(re.findall(r"\\ref\{([^}]+)\}", report))
    assert references, "The report contains no cross-references"
    assert not references - labels, f"Dangling references: {sorted(references - labels)}"


def test_labels_are_unique() -> None:
    """Duplicate labels would silently misdirect a cross-reference."""
    labels = re.findall(r"\\label\{([^}]+)\}", _report())
    duplicated = sorted({label for label in labels if labels.count(label) > 1})
    assert not duplicated, f"Duplicated labels: {duplicated}"


def test_raw_column_identifiers_do_not_leak_into_tables() -> None:
    """Tables must show readable labels, not the underlying column names."""
    report = _report()
    forbidden = (
        r"central\_government",
        r"regional\_local\_government",
        r"social\_security\_funds",
        r"general\_government",
        r"\_m\_eur",
        r"\_pct\_gdp",
    )
    leaked = [identifier for identifier in forbidden if identifier in report]
    assert not leaked, f"Raw identifiers rendered in the report: {leaked}"


def test_headline_numbers_match_the_panel() -> None:
    """The at-a-glance section must restate the panel, not a stale copy of it."""
    report = _report()
    annual = pd.read_csv(ROOT / "data" / "processed" / "annual_balance_metrics_1977_2025.csv")
    latest = annual.loc[annual["year"].idxmax()]
    year = int(latest["year"])
    assert f"General Government balance, {year}" in report
    assert f"{latest['general_government_balance_m_eur']:,.0f} M EUR" in report
    assert f"{latest['social_security_balance_m_eur']:,.0f} M EUR" in report


def test_positive_balance_years_are_reported_from_the_summary() -> None:
    """The abstract must list the calculated positive-balance years."""
    summary = json.loads(
        (ROOT / "outputs" / "metrics" / "analysis_summary.json").read_text(encoding="utf-8")
    )
    years = [int(year) for year in summary["balance_summary"]["positive_aggregate_balance_years"]]
    report = _report()
    assert f"positive in {len(years)} of" in report
    for year in years:
        assert str(year) in report


def test_report_declares_its_repository_version() -> None:
    """An archived report should identify the build it came from."""
    import tomllib

    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    assert f"Repository version {version}" in _report()


def test_report_declares_the_provisional_years_it_relies_on() -> None:
    """The years discussed in most detail are provisional, and must say so."""
    panel = pd.read_csv(ROOT / "data" / "processed" / "fiscal_balances_1977_2025.csv")
    provisional = [
        int(year) for year in panel.loc[panel["vintage_status"].eq("provisional"), "year"]
    ]
    assert provisional, "The panel has no provisional years to report"
    report = _report()
    assert "provisional" in report.lower()
    for year in provisional:
        assert str(year) in report
    assert "Data vintage" in report


def test_weak_regressions_live_in_an_appendix_not_the_body() -> None:
    """The co-movement estimates must not sit among the results the report stands on."""
    report = _report()
    appendix = report.index(r"\appendix")
    comovement = report.index(r"\section{Descriptive Macroeconomic Co-Movement}")
    assert comovement > appendix, "Co-movement section is still in the report body"
    for heading in (
        r"\section{Long-Run Subsector Decomposition}",
        r"\section{Social Security Funds: Revenue Composition and Internal Systems}",
        r"\section{Primary Balance and Interest}",
        r"\section{Methodological Limitations}",
    ):
        assert report.index(heading) < appendix, f"{heading} was pushed into the appendix"


def test_report_states_the_regime_split_rather_than_only_pooled_means() -> None:
    """Pooled magnitudes describe neither regime, so both must be present."""
    report = _report()
    regime = pd.read_csv(ROOT / "outputs" / "tables" / "persistence_by_regime.csv")
    aggregate = regime.loc[regime["sector"].eq("general_government")].set_index("regime")
    for key in ("1977-1994_historical", "1995-2025_modern"):
        value = float(aggregate.loc[key, "mean_balance_pct_gdp"])
        assert f"{value:.2f}" in report, f"Regime mean for {key} is not restated"


def test_report_shows_the_new_evidence_tables() -> None:
    """Each artefact added to the pipeline must actually be shown, not just persisted."""
    labels = set(re.findall(r"\\label\{tab:([^}]+)\}", _report()))
    expected = {
        "validation",
        "movements",
        "revexpepisodes",
        "persistenceregime",
        "breakstability",
        "primarysigns",
        "ssfboundary",
    }
    assert expected <= labels, f"Missing tables: {sorted(expected - labels)}"


def test_attribution_figures_disclose_their_year_windows() -> None:
    """A stacked bar chart cannot show that years are missing from its ends."""
    report = _report()
    for window in ("1996--2025", "1978--1994"):
        assert window in report, f"Attribution window {window} is not stated"


def test_no_unescaped_percent_signs_silently_comment_out_prose() -> None:
    """An unescaped ``%`` starts a LaTeX comment and swallows the rest of the line.

    This fails silently: the document still compiles, and text simply disappears.
    Escaped ``\\%``, a trailing ``%`` used to suppress a line break, and a whole-line
    comment are all legitimate; anything else is a formatting bug.
    """
    offenders: list[str] = []
    for number, line in enumerate(_report().splitlines(), start=1):
        if line.lstrip().startswith("%"):
            continue
        for position, character in enumerate(line):
            if character != "%":
                continue
            if position > 0 and line[position - 1] == "\\":
                continue
            if position == len(line) - 1:
                continue
            offenders.append(f"line {number}: {line.strip()}")
    assert not offenders, "Unescaped percent signs found:\n" + "\n".join(offenders)


def test_report_has_no_unbalanced_environments() -> None:
    """Every float environment opened must be closed."""
    report = _report()
    for environment in ("table", "figure", "tabular", "abstract", "enumerate", "document"):
        opened = len(re.findall(rf"\\begin\{{{environment}\}}", report))
        closed = len(re.findall(rf"\\end\{{{environment}\}}", report))
        assert opened == closed, f"Unbalanced {environment}: {opened} begin, {closed} end"
