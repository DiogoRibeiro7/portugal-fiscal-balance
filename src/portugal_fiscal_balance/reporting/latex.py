"""LaTeX building blocks for the generated report.

The report is assembled entirely from persisted analysis artefacts, so this
module handles presentation only: escaping, number formatting and the float
environments. Keeping it separate from ``render.py`` means the document
structure stays readable and the same formatting rules apply to every table and
figure.

Two conventions are enforced here rather than left to each call site:

- numeric columns are right-aligned and text columns left-aligned, derived from
  the dataframe dtypes instead of hand-written column specifications;
- a table is shrunk to the text width only when it would otherwise overflow, so
  narrow tables keep the body font size instead of being stretched.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

ESCAPES: Final[dict[str, str]] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

MISSING: Final[str] = "--"

#: Placeholders substituted by :func:`preamble`.
_TITLE_TOKEN: Final[str] = "<<TITLE>>"
_AUTHOR_TOKEN: Final[str] = "<<AUTHOR>>"
_SUBJECT_TOKEN: Final[str] = "<<SUBJECT>>"
_DATE_TOKEN: Final[str] = "<<DATE>>"

_PREAMBLE: Final[str] = r"""\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage[margin=2.4cm]{geometry}
\usepackage{caption}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{hyperref}

\definecolor{reportlink}{HTML}{1C5CAB}

% File paths are typeset with \path. Its default break glue is stretchable, which
% opens visible gaps inside a path in justified text; remove the stretch.
\setlength{\Urlmuskip}{0mu plus 0mu}

\hypersetup{
  pdftitle={<<TITLE>>},
  pdfauthor={<<AUTHOR>>},
  pdfsubject={<<SUBJECT>>},
  colorlinks=true,
  linkcolor=reportlink,
  urlcolor=reportlink,
  citecolor=reportlink
}

\graphicspath{{../outputs/figures/}}

\captionsetup{
  font=small,
  labelfont=bf,
  justification=raggedright,
  singlelinecheck=false,
  skip=6pt
}

\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.15}
\setlist[enumerate]{itemsep=2pt, topsep=4pt}
\setlist[itemize]{itemsep=2pt, topsep=4pt}

% Shrink a table to the text width only if it would otherwise overflow, so that
% narrow tables are not stretched away from the body font size.
\newcommand{\fitwidth}[1]{%
  \resizebox{\ifdim\width>\linewidth\linewidth\else\width\fi}{!}{#1}%
}

\title{<<TITLE>>}
\author{<<AUTHOR>>}
\date{<<DATE>>}
"""


def preamble(*, title: str, author: str, subject: str, date: str = "") -> str:
    """Return the document preamble with its metadata filled in.

    ``date`` is deliberately not a build timestamp: the pipeline is
    deterministic and its outputs are committed, so the document must not change
    when it is rebuilt from unchanged inputs.
    """
    return (
        _PREAMBLE.replace(_TITLE_TOKEN, title)
        .replace(_AUTHOR_TOKEN, author)
        .replace(_SUBJECT_TOKEN, subject)
        .replace(_DATE_TOKEN, date)
    )


def escape(value: Any) -> str:
    """Escape a value for LaTeX text mode."""
    return "".join(ESCAPES.get(character, character) for character in str(value))


def number(value: Any, digits: int = 1) -> str:
    """Format one value for prose: thousands separators for numbers, escaped text otherwise."""
    if value is None:
        return MISSING
    if isinstance(value, bool | np.bool_):
        return "yes" if bool(value) else "no"
    if isinstance(value, int | np.integer):
        return f"{int(value):,}"
    if isinstance(value, float | np.floating):
        if pd.isna(value):
            return MISSING
        return f"{float(value):,.{digits}f}"
    if pd.isna(value):
        return MISSING
    return escape(value)


def _is_year_column(label: str) -> bool:
    """Years are labels, not quantities, so they carry no thousands separator."""
    return "year" in label.lower()


def _cell(value: Any, digits: int, *, is_year: bool) -> str:
    """Format one table cell.

    Numeric columns are formatted with a fixed number of decimals regardless of
    whether the underlying dtype is integer or float, so a column never mixes
    ``-4,611`` with ``-4,557.7``.
    """
    if value is None:
        return MISSING
    if isinstance(value, bool | np.bool_):
        return "yes" if bool(value) else "no"
    if isinstance(value, int | np.integer | float | np.floating):
        if pd.isna(value):
            return MISSING
        if is_year:
            return f"{int(value)}"
        return f"{float(value):,.{digits}f}"
    if pd.isna(value):
        return MISSING
    return escape(value)


def _alignment(frame: pd.DataFrame) -> str:
    """Right-align numeric columns and left-align everything else."""
    return "".join(
        "r" if pd.api.types.is_numeric_dtype(frame[column]) else "l" for column in frame.columns
    )


def _column_digits(
    frame: pd.DataFrame, digits: int, overrides: dict[str, int] | None
) -> dict[str, int]:
    """Resolve the decimal places used for each column."""
    resolved = dict.fromkeys(frame.columns.astype(str), digits)
    for column, value in (overrides or {}).items():
        resolved[column] = value
    return resolved


def table(
    frame: pd.DataFrame,
    *,
    caption: str,
    label: str,
    digits: int = 1,
    column_digits: dict[str, int] | None = None,
    mono_columns: set[str] | None = None,
    note: str | None = None,
    placement: str = "htbp",
    size: str = "small",
) -> str:
    """Render a dataframe as a captioned, labelled and referenceable table.

    Column headers, the caption and the note are author-written and passed
    through as LaTeX. Cell values come from the persisted data and are escaped,
    so a stray identifier or path in a table body cannot break the document.
    """
    if frame.empty:
        return f"\\emph{{{escape(caption)}: no observations available.}}\n"
    resolved = _column_digits(frame, digits, column_digits)
    years = {str(column): _is_year_column(str(column)) for column in frame.columns}
    monospaced = mono_columns or set()
    header = " & ".join(str(column) for column in frame.columns) + r" \\"
    rows = [
        " & ".join(
            rf"\texttt{{{cell}}}" if str(column) in monospaced else cell
            for column, cell in (
                (column, _cell(value, resolved[str(column)], is_year=years[str(column)]))
                for column, value in zip(frame.columns, record, strict=True)
            )
        )
        + r" \\"
        for record in frame.itertuples(index=False, name=None)
    ]
    lines = [
        rf"\begin{{table}}[{placement}]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{tab:{label}}}",
        rf"\{size}",
        r"\fitwidth{%",
        rf"\begin{{tabular}}{{@{{}}{_alignment(frame)}@{{}}}}",
        r"\toprule",
        header,
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}%",
        r"}",
    ]
    if note is not None:
        lines.extend([r"\par\smallskip", rf"\begin{{minipage}}{{\linewidth}}\footnotesize\itshape {note}\end{{minipage}}"])
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def figure(
    filename: str,
    *,
    caption: str,
    label: str,
    width: float = 1.0,
    placement: str = "htbp",
) -> str:
    """Render a persisted figure as a captioned, labelled and referenceable float."""
    return "\n".join(
        [
            rf"\begin{{figure}}[{placement}]",
            r"\centering",
            rf"\includegraphics[width={width:g}\linewidth]{{{filename}}}",
            rf"\caption{{{caption}}}",
            rf"\label{{fig:{label}}}",
            r"\end{figure}",
        ]
    ) + "\n"


def ref_table(label: str) -> str:
    """Reference a table by label."""
    return rf"Table~\ref{{tab:{label}}}"


def ref_figure(label: str) -> str:
    """Reference a figure by label."""
    return rf"Figure~\ref{{fig:{label}}}"
