"""Structural tests for the authored manuscript in ``paper/``.

The manuscript mixes authored prose with generated inputs, which is a weaker
arrangement than the fully generated report: a person can type a number into a
section file, and nothing in LaTeX would object.

These tests close that gap. They check that every quantity the prose cites is a
macro the pipeline defined, that no digit-grouped money value appears in authored
text, and that every include, figure and citation resolves.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
SECTIONS = PAPER / "sections"
GENERATED = PAPER / "generated"

#: Macro names are CamelCase starting with a capital. Almost every LaTeX and
#: package command the manuscript uses is lower-case, so this pattern isolates the
#: repository's own macros without needing a list of LaTeX built-ins. The
#: lookbehind keeps ``\\`` -- a line break followed by a capitalised word -- from
#: reading as a macro named after that word.
_MACRO_USE = re.compile(r"(?<!\\)\\([A-Z][A-Za-z]*)")
_MACRO_DEF = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}")

#: The capitalised commands that are LaTeX's or a package's, not ours.
_LATEX_CAPITALS = frozenset({"Delta", "Urlmuskip", "LaTeX", "TeX"})


def _strip_comments(text: str) -> str:
    """Remove LaTeX comments, so commented-out text is not treated as prose.

    Without this a note explaining why ``\\today`` is avoided would itself trip a
    test looking for ``\\today``.
    """
    lines: list[str] = []
    for line in text.splitlines():
        cleaned: list[str] = []
        for position, character in enumerate(line):
            if character == "%" and (position == 0 or line[position - 1] != "\\"):
                break
            cleaned.append(character)
        lines.append("".join(cleaned))
    return "\n".join(lines)


def _authored_sources() -> dict[Path, str]:
    """Return every hand-authored LaTeX file with its text, comments removed."""
    paths = [PAPER / "paper.tex", *sorted(SECTIONS.glob("*.tex"))]
    missing = [path for path in paths if not path.exists()]
    assert not missing, f"Authored sources missing: {missing}"
    return {path: _strip_comments(path.read_text(encoding="utf-8")) for path in paths}


def _defined_macros() -> set[str]:
    """Return every macro name defined by the pipeline or in the preamble."""
    definitions: set[str] = set()
    for path in (GENERATED / "macros.tex", PAPER / "paper.tex"):
        assert path.exists(), f"Expected {path} to exist; run the pipeline"
        definitions.update(_MACRO_DEF.findall(path.read_text(encoding="utf-8")))
    return definitions


def test_generated_inputs_exist() -> None:
    """The pipeline must have written the manuscript's generated inputs."""
    assert (GENERATED / "macros.tex").exists()
    tables = sorted(GENERATED.glob("tab_*.tex"))
    assert tables, "No generated tables found in paper/generated/"


def test_macro_file_is_substantive() -> None:
    """A near-empty macro file would mean the prose is carrying its own numbers."""
    macros = _MACRO_DEF.findall((GENERATED / "macros.tex").read_text(encoding="utf-8"))
    assert len(macros) >= 40, f"Only {len(macros)} macros defined"
    assert len(macros) == len(set(macros)), "Duplicate macro definitions"


def test_every_macro_the_prose_cites_is_defined() -> None:
    """This is the guarantee the manuscript rests on.

    An undefined macro is a LaTeX error rather than a silent blank, so the build
    already catches it. Testing it here fails faster and, more importantly, states
    the invariant: authored prose may not invent a quantity.
    """
    defined = _defined_macros() | _LATEX_CAPITALS
    unknown: dict[str, set[str]] = {}
    for path, text in _authored_sources().items():
        used = set(_MACRO_USE.findall(text)) - defined
        if used:
            unknown[path.name] = used
    assert not unknown, f"Undefined macros cited in authored prose: {unknown}"


def test_every_defined_macro_is_actually_cited() -> None:
    """An unused macro is dead weight that invites a stale number later."""
    authored = "\n".join(_authored_sources().values())
    used = set(_MACRO_USE.findall(authored))
    defined = _MACRO_DEF.findall((GENERATED / "macros.tex").read_text(encoding="utf-8"))
    unused = sorted(set(defined) - used)
    assert not unused, f"Generated macros never cited by the prose: {unused}"


def test_authored_prose_contains_no_transcribed_money_values() -> None:
    """A digit-grouped number in authored text is the signature of a hand-copied value.

    Money in this manuscript is always a macro, and the macros carry their own
    thousands separators. So a literal ``7,065`` in a section file means someone
    typed a value the pipeline was supposed to supply.
    """
    grouped = re.compile(r"\d{1,3},\d{3}")
    offenders: dict[str, list[str]] = {}
    for path, text in _authored_sources().items():
        hits = grouped.findall(text)
        if hits:
            offenders[path.name] = hits
    assert not offenders, f"Transcribed money values in authored prose: {offenders}"


def test_every_included_file_resolves() -> None:
    """An \\input pointing at nothing would drop a table or a section silently."""
    missing: list[str] = []
    for path, text in _authored_sources().items():
        for target in re.findall(r"\\input\{([^}]+)\}", text):
            candidate = PAPER / f"{target}.tex"
            if not candidate.exists():
                missing.append(f"{path.name} -> {target}")
    assert not missing, f"Unresolved includes: {missing}"


def test_every_included_figure_exists() -> None:
    """Figures are read from outputs/figures, not copied, so they must be present."""
    figures_dir = ROOT / "outputs" / "figures"
    missing: list[str] = []
    for _path, text in _authored_sources().items():
        for name in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", text):
            if not (figures_dir / name).exists():
                missing.append(name)
    assert missing == [], f"Referenced figures do not exist: {missing}"


def test_every_citation_resolves_to_a_bibliography_entry() -> None:
    """A dangling \\citep renders as a question mark and reads as carelessness."""
    bibliography = (PAPER / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bibliography))
    assert keys, "No entries parsed from references.bib"

    cited: set[str] = set()
    for _path, text in _authored_sources().items():
        for group in re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}", text):
            cited.update(key.strip() for key in group.split(","))
    assert cited, "The manuscript cites nothing"
    assert cited <= keys, f"Citations with no bibliography entry: {sorted(cited - keys)}"


def test_every_bibliography_entry_is_cited() -> None:
    """An uncited entry suggests a reference list assembled rather than used."""
    bibliography = (PAPER / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bibliography))
    cited: set[str] = set()
    for _path, text in _authored_sources().items():
        for group in re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}", text):
            cited.update(key.strip() for key in group.split(","))
    assert not keys - cited, f"Bibliography entries never cited: {sorted(keys - cited)}"


def test_cross_references_resolve() -> None:
    """Every \\ref must point at a label the manuscript defines."""
    combined = "\n".join(_authored_sources().values())
    generated = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(GENERATED.glob("*.tex"))
    )
    labels = set(re.findall(r"\\label\{([^}]+)\}", combined + "\n" + generated))
    references = set(re.findall(r"\\(?:eq)?ref\{([^}]+)\}", combined))
    assert references, "The manuscript contains no cross-references"
    assert not references - labels, f"Dangling references: {sorted(references - labels)}"


def test_manuscript_does_not_carry_a_build_date() -> None:
    """A build timestamp would make the committed PDF change on every rebuild."""
    text = _strip_comments((PAPER / "paper.tex").read_text(encoding="utf-8"))
    assert r"\date{" in text
    assert r"\today" not in text, "The manuscript title page carries a build date"
    assert r"\RepositoryVersion" in text


def test_generated_inputs_are_marked_as_generated() -> None:
    """Anyone opening a generated file should be told not to edit it."""
    for path in sorted(GENERATED.glob("*.tex")):
        head = path.read_text(encoding="utf-8")[:400]
        if path.name == "macros.tex":
            assert "Do not edit" in head, f"{path.name} carries no warning"
