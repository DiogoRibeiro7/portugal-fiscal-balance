"""Figures shared by the deterministic pipeline and the analysis notebooks.

Every builder returns a Matplotlib :class:`~matplotlib.figure.Figure` instead of
writing a file, so a notebook can display exactly the figure the pipeline
persists without reimplementing any plotting logic. ``save_figure`` is the only
function that touches the filesystem.

Encoding rules applied throughout:

- a subsector keeps the same hue in every figure, so colour identifies the
  entity and never its rank or magnitude;
- the categorical order is fixed and was validated for colour-vision
  deficiency separation on the light chart surface;
- sign is encoded with a diverging blue/red pair and a neutral midpoint;
- series are labelled directly at the end of the line as well as in the legend,
  because three of the categorical hues sit below a 3:1 contrast ratio against
  the surface;
- source gaps such as the missing 1996-1999 subsector accounts are reindexed to
  ``NaN`` so no line is drawn across a period without observations.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cycler import cycler
from matplotlib.axes import Axes
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from portugal_fiscal_balance.schemas import SECTOR_BALANCE_PCT_GDP, SECTOR_LABELS

SURFACE: Final[str] = "#fcfcfb"
INK_PRIMARY: Final[str] = "#0b0b0b"
INK_SECONDARY: Final[str] = "#52514e"
INK_MUTED: Final[str] = "#898781"
GRIDLINE: Final[str] = "#e1e0d9"
BASELINE: Final[str] = "#c3c2b7"

#: Fixed categorical order, validated for CVD separation on the light surface.
SERIES_COLOURS: Final[tuple[str, ...]] = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4")

#: Colour follows the entity: a subsector has one hue across the whole report.
SECTOR_COLOURS: Final[dict[str, str]] = {
    "general_government": SERIES_COLOURS[0],
    "central_government": SERIES_COLOURS[1],
    "regional_local_government": SERIES_COLOURS[2],
    "social_security_funds": SERIES_COLOURS[3],
    "non_ssf": SERIES_COLOURS[4],
}

#: Readable labels for the wide balance columns of the canonical panel.
METRIC_LABELS: Final[dict[str, str]] = {
    "general_government_balance_m_eur": "General Government",
    "central_government_balance_m_eur": "Central Government",
    "regional_local_balance_m_eur": "Regional and Local",
    "social_security_balance_m_eur": "Social Security Funds",
}

#: Statistical regimes as recorded in the processed panels, in source order.
REGIME_COLOURS: Final[dict[str, str]] = {
    "historical_long_series": SERIES_COLOURS[0],
    "esa2010_modern": SERIES_COLOURS[1],
}

REGIME_LABELS: Final[dict[str, str]] = {
    "historical_long_series": "Historical long series",
    "esa2010_modern": "Modern ESA 2010 workbook",
}

#: Diverging pair for signed quantities, with a neutral midpoint.
POSITIVE_COLOUR: Final[str] = "#2a78d6"
NEGATIVE_COLOUR: Final[str] = "#e34948"
NEUTRAL_COLOUR: Final[str] = "#f0efec"

SPLICE_YEAR: Final[int] = 1995

HOUSE_STYLE: Final[dict[str, object]] = {
    "figure.figsize": (10.0, 4.6),
    "figure.dpi": 100,
    "figure.facecolor": SURFACE,
    "figure.constrained_layout.use": True,
    "savefig.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.labelcolor": INK_SECONDARY,
    "axes.labelsize": 10.0,
    "axes.titlesize": 12.5,
    "axes.titlecolor": INK_PRIMARY,
    "axes.titlelocation": "left",
    "axes.titlepad": 9.0,
    "axes.prop_cycle": cycler(color=list(SERIES_COLOURS)),
    "grid.color": GRIDLINE,
    "grid.linestyle": "-",
    "grid.linewidth": 0.8,
    "lines.linewidth": 2.0,
    "lines.markersize": 5.0,
    "lines.solid_capstyle": "round",
    "font.size": 10.0,
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"],
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "xtick.labelsize": 9.0,
    "ytick.labelsize": 9.0,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "legend.frameon": False,
    "legend.fontsize": 9.5,
    "legend.labelcolor": INK_SECONDARY,
}


def apply_house_style() -> None:
    """Apply the repository figure style.

    Builders call this themselves, so a notebook figure is identical to the
    persisted one even if the notebook never sets any Matplotlib option.
    """
    plt.rcParams.update(cast(Any, HOUSE_STYLE))


def save_figure(fig: Figure, path: Path, *, dpi: int = 180) -> None:
    """Write a figure to disk at publication resolution and release it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _panel(
    *,
    title: str,
    ylabel: str,
    xlabel: str = "Year",
    height: float = 4.6,
    grid_axis: Literal["both", "x", "y"] = "y",
) -> tuple[Figure, Axes]:
    """Create a single-panel figure carrying the house style."""
    apply_house_style()
    fig, ax = plt.subplots(figsize=(10.0, height))
    ax.set_title(title, pad=30.0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(visible=True, axis=grid_axis)
    ax.set_axisbelow(True)
    if xlabel == "Year":
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return fig, ax


def _legend(ax: Axes, *, ncol: int = 4) -> None:
    """Place the legend in a row above the plot, where no mark can collide with it."""
    handles, labels = ax.get_legend_handles_labels()
    if len(labels) < 2:
        return
    ax.legend(
        handles,
        labels,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        borderaxespad=0.0,
        ncol=ncol,
        columnspacing=1.6,
        handlelength=1.7,
    )


def _zero_rule(ax: Axes) -> None:
    """Draw the hairline zero reference used by every signed balance chart."""
    ax.axhline(0.0, color=BASELINE, linewidth=1.0, zorder=1)


def _reference_rule(ax: Axes, value: float, label: str) -> None:
    """Draw and label a horizontal reference level."""
    ax.axhline(value, color=INK_MUTED, linewidth=1.0, zorder=1)
    ax.annotate(
        label,
        xy=(0.006, value),
        xycoords=("axes fraction", "data"),
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=INK_MUTED,
    )


def _splice_marker(ax: Axes, *, year: int = SPLICE_YEAR, label: str = "1995 source splice") -> None:
    """Mark the known statistical splice without implying an economic event."""
    ax.axvline(year, color=BASELINE, linewidth=1.0, zorder=1)
    ax.annotate(
        label,
        xy=(year, 0.985),
        xycoords=("data", "axes fraction"),
        xytext=(4, 0),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8.5,
        color=INK_MUTED,
    )


def _end_labels(ax: Axes, points: Sequence[tuple[str, float, float, str]]) -> None:
    """Label series directly at their final observation.

    Labels are nudged apart vertically so a dense right-hand edge stays legible.
    This is the relief required by the low-contrast categorical hues: identity is
    never carried by colour alone.
    """
    if not points:
        return
    bottom, top = ax.get_ylim()
    minimum_gap = 0.055 * (top - bottom)
    ordered = sorted(points, key=lambda item: item[2])
    placed: list[float] = []
    for label, x_value, y_value, colour in ordered:
        y_label = y_value
        if placed and y_label - placed[-1] < minimum_gap:
            y_label = placed[-1] + minimum_gap
        placed.append(y_label)
        ax.annotate(
            label,
            xy=(x_value, y_label),
            xytext=(7, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9.0,
            color=colour,
            clip_on=False,
        )


def _gap_aware(frame: pd.DataFrame, column: str) -> tuple[np.ndarray, np.ndarray]:
    """Return year/value arrays reindexed over the full span, with gaps as ``NaN``.

    Subsector accounts have no 1996-1999 observations. Reindexing keeps that gap
    visible as a break in the line instead of interpolating it away visually.
    """
    series = frame.set_index("year")[column].sort_index()
    years = np.arange(int(series.index.min()), int(series.index.max()) + 1)
    values = series.reindex(years).to_numpy(dtype=float)
    return years, values


def _last_observation(years: np.ndarray, values: np.ndarray) -> tuple[float, float] | None:
    """Return the last finite point of a possibly gapped series."""
    finite = np.flatnonzero(np.isfinite(values))
    if finite.size == 0:
        return None
    index = int(finite[-1])
    return float(years[index]), float(values[index])


def _break_after(
    years: np.ndarray, values: np.ndarray, year: int
) -> tuple[np.ndarray, np.ndarray]:
    """Insert a gap in the drawn path immediately after ``year``.

    A vertical rule labelling the 1995 splice is a weaker signal than an actual
    discontinuity: the eye follows an unbroken line straight across it and reads
    continuity the caption is trying to deny. Splitting the path makes the two
    source families visually separate series.
    """
    position = int(np.searchsorted(years, year, side="right"))
    if position <= 0 or position >= len(years):
        return years, values
    return (
        np.concatenate([years[:position], [np.nan], years[position:]]),
        np.concatenate([values[:position], [np.nan], values[position:]]),
    )


def _line(
    ax: Axes,
    frame: pd.DataFrame,
    column: str,
    *,
    label: str,
    colour: str,
    marker: str | None = None,
    break_after: int | None = None,
) -> tuple[str, float, float, str] | None:
    """Plot one gap-aware series and return its end-label anchor."""
    years, values = _gap_aware(frame, column)
    end = _last_observation(years, values)
    if break_after is not None:
        years, values = _break_after(years, values, break_after)
    ax.plot(years, values, label=label, color=colour, marker=marker, zorder=3)
    if end is None:
        return None
    return (label, end[0], end[1], colour)


def _signed_stack(
    ax: Axes,
    years: np.ndarray,
    layers: Sequence[tuple[str, np.ndarray, str]],
) -> None:
    """Draw a signed stacked bar chart.

    Positive and negative contributions stack away from zero independently, so
    the visible column height equals the arithmetic sum of the layers.
    """
    positions = years.astype(float, copy=False)
    up = np.zeros(positions.shape)
    down = np.zeros(positions.shape)
    for label, values, colour in layers:
        clean = np.nan_to_num(np.asarray(values, dtype=float))
        bottom = np.where(clean >= 0.0, up, down)
        ax.bar(
            positions,
            clean,
            bottom=bottom,
            width=0.74,
            label=label,
            color=colour,
            edgecolor=SURFACE,
            linewidth=1.2,
            zorder=2,
        )
        up = up + np.clip(clean, 0.0, None)
        down = down + np.clip(clean, None, 0.0)


def balances_by_subsector(
    panel: pd.DataFrame,
    *,
    title: str = "Portugal: fiscal balance by subsector, 1977-2025",
    splice_year: int | None = SPLICE_YEAR,
) -> Figure:
    """Plot the four balance ratios that make up the core accounting identity.

    Each series is drawn as two segments either side of the splice year, so the
    change of source family is a visible discontinuity and not just a labelled
    rule that an unbroken line runs straight through.
    """
    fig, ax = _panel(title=title, ylabel="Net lending (+) / net borrowing (-), % GDP")
    anchors = [
        _line(
            ax,
            panel,
            column,
            label=SECTOR_LABELS[sector],
            colour=SECTOR_COLOURS[sector],
            break_after=None if splice_year is None else splice_year - 1,
        )
        for sector, column in SECTOR_BALANCE_PCT_GDP.items()
    ]
    _zero_rule(ax)
    if splice_year is not None:
        _splice_marker(ax, year=splice_year)
    _legend(ax, ncol=4)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def subsector_contributions(panel: pd.DataFrame, *, start_year: int = 1977) -> Figure:
    """Show how the aggregate balance decomposes into subsector contributions."""
    frame = panel.loc[panel["year"].ge(start_year)].sort_values("year")
    fig, ax = _panel(
        title="Subsector contributions to the General Government balance",
        ylabel="% GDP",
        height=5.0,
    )
    _signed_stack(
        ax,
        frame["year"].to_numpy(dtype=float),
        [
            (
                SECTOR_LABELS["central_government"],
                frame["central_government_balance_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["central_government"],
            ),
            (
                SECTOR_LABELS["regional_local_government"],
                frame["regional_local_balance_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["regional_local_government"],
            ),
            (
                SECTOR_LABELS["social_security_funds"],
                frame["social_security_balance_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["social_security_funds"],
            ),
        ],
    )
    ax.plot(
        frame["year"],
        frame["general_government_balance_pct_gdp"],
        color=INK_PRIMARY,
        linewidth=1.6,
        label="General Government (identity total)",
        zorder=4,
    )
    _zero_rule(ax)
    _legend(ax, ncol=2)
    return fig


def offset_ratio(metrics: pd.DataFrame) -> Figure:
    """Plot the SSF offset ratio for years where the ratio is defined."""
    frame = metrics.dropna(subset=["ssf_offset_ratio"]).sort_values("year")
    fig, ax = _panel(
        title="Social Security Funds offset ratio, defined years only",
        ylabel="SSF balance / |non-SSF balance|",
    )
    ax.plot(
        frame["year"],
        frame["ssf_offset_ratio"],
        color=SECTOR_COLOURS["social_security_funds"],
        marker="o",
        markeredgecolor=SURFACE,
        markeredgewidth=1.2,
        label="Offset ratio",
        zorder=3,
    )
    _reference_rule(ax, 1.0, "ratio = 1: SSF balance equals the non-SSF shortfall")
    _splice_marker(ax)
    _legend(ax)
    return fig


def balance_change_attribution(
    changes: pd.DataFrame,
    *,
    start_year: int,
    end_year: int,
) -> Figure:
    """Attribute each annual change in the aggregate balance to the subsectors.

    The window is a required argument and is written into the title, because a
    stacked bar chart gives the reader no way to tell that years are missing from
    the ends. The value plotted is the annual change scaled by current-year GDP
    rather than the nominal change, which keeps the historical and modern windows
    on one comparable axis; the underlying tables report million euro.
    """
    frame = changes.loc[changes["year"].between(start_year, end_year)].sort_values("year")
    fig, ax = _panel(
        title=(
            "Year-to-year change in the General Government balance, by subsector, "
            f"{start_year}-{end_year}"
        ),
        ylabel="Annual change, % of current-year GDP",
        height=5.0,
    )
    _signed_stack(
        ax,
        frame["year"].to_numpy(dtype=float),
        [
            (
                SECTOR_LABELS["central_government"],
                frame["central_change_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["central_government"],
            ),
            (
                SECTOR_LABELS["regional_local_government"],
                frame["regional_local_change_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["regional_local_government"],
            ),
            (
                SECTOR_LABELS["social_security_funds"],
                frame["ssf_change_pct_gdp"].to_numpy(dtype=float),
                SECTOR_COLOURS["social_security_funds"],
            ),
        ],
    )
    ax.plot(
        frame["year"],
        frame["aggregate_change_pct_gdp"],
        color=INK_PRIMARY,
        linewidth=1.6,
        label="Aggregate change (identity total)",
        zorder=4,
    )
    _zero_rule(ax)
    _legend(ax, ncol=2)
    return fig


def revenue_expenditure(accounts: pd.DataFrame, sector: str) -> Figure:
    """Plot revenue, expenditure and the resulting balance for one sector."""
    frame = accounts.loc[accounts["sector"].eq(sector)].sort_values("year")
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=f"Revenue, expenditure and balance: {label}",
        ylabel="% GDP",
    )
    anchors = [
        _line(ax, frame, "total_revenue_pct_gdp", label="Revenue", colour=SERIES_COLOURS[0]),
        _line(ax, frame, "total_expenditure_pct_gdp", label="Expenditure", colour=SERIES_COLOURS[1]),
        _line(ax, frame, "balance_pct_gdp", label="Balance", colour=SERIES_COLOURS[2]),
    ]
    _zero_rule(ax)
    _splice_marker(ax)
    _legend(ax, ncol=3)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def revenue_expenditure_changes(
    changes: pd.DataFrame,
    sector: str,
    *,
    start_year: int,
    end_year: int,
) -> Figure:
    """Show the exact decomposition of a balance change into revenue and expenditure.

    As with the attribution chart, the window is required and appears in the
    title: paired bars give no visual cue that the series has been truncated.
    """
    selected = changes["sector"].eq(sector) & changes["year"].between(start_year, end_year)
    frame = changes.loc[selected].sort_values("year")
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=(
            "Change in balance decomposed into revenue and expenditure: "
            f"{label}, {start_year}-{end_year}"
        ),
        ylabel="Annual change, million euro",
    )
    positions = frame["year"].to_numpy(dtype=float)
    ax.bar(
        positions - 0.2,
        frame["revenue_change_m_eur"],
        width=0.38,
        label="Change in revenue",
        color=SERIES_COLOURS[0],
        edgecolor=SURFACE,
        linewidth=1.2,
        zorder=2,
    )
    ax.bar(
        positions + 0.2,
        frame["expenditure_change_m_eur"],
        width=0.38,
        label="Change in expenditure",
        color=SERIES_COLOURS[1],
        edgecolor=SURFACE,
        linewidth=1.2,
        zorder=2,
    )
    ax.plot(
        positions,
        frame["balance_change_m_eur"],
        color=INK_PRIMARY,
        linewidth=1.6,
        label="Change in balance",
        zorder=4,
    )
    _zero_rule(ax)
    _legend(ax, ncol=3)
    return fig


def balance_sign_states(panel: pd.DataFrame) -> Figure:
    """Show the sign of every subsector balance as a year-by-sector grid."""
    apply_house_style()
    sectors = list(SECTOR_BALANCE_PCT_GDP)
    years = panel["year"].to_numpy(dtype=int)
    grid = np.vstack(
        [np.sign(panel[SECTOR_BALANCE_PCT_GDP[sector]].to_numpy(dtype=float)) for sector in sectors]
    )
    fig, ax = plt.subplots(figsize=(10.0, 3.1))
    ax.set_title("Sign of the annual balance by subsector", pad=30.0)
    colourmap = ListedColormap([NEGATIVE_COLOUR, NEUTRAL_COLOUR, POSITIVE_COLOUR])
    ax.imshow(
        grid,
        aspect="auto",
        cmap=colourmap,
        norm=BoundaryNorm([-1.5, -0.5, 0.5, 1.5], colourmap.N),
        extent=(float(years[0]) - 0.5, float(years[-1]) + 0.5, len(sectors) - 0.5, -0.5),
        interpolation="nearest",
    )
    ax.set_yticks(range(len(sectors)), [SECTOR_LABELS[sector] for sector in sectors])
    ax.set_xticks(np.arange(1980, int(years[-1]) + 1, 5))
    ax.set_xlabel("Year")
    ax.grid(visible=False)
    ax.tick_params(axis="y", length=0, labelcolor=INK_SECONDARY)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(float(years[0]) - 0.5, float(years[-1]) + 1.0), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sectors)), minor=True)
    ax.grid(visible=True, which="minor", color=SURFACE, linewidth=1.2)
    ax.tick_params(which="minor", length=0)
    ax.legend(
        handles=[
            Patch(facecolor=POSITIVE_COLOUR, label="Net lending (+)"),
            Patch(facecolor=NEGATIVE_COLOUR, label="Net borrowing (-)"),
        ],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        borderaxespad=0.0,
        ncol=2,
    )
    return fig


def structural_break_segments(panel: pd.DataFrame, breaks: pd.DataFrame, *, sector: str, regime: str) -> Figure:
    """Overlay the selected piecewise-constant segment means on one balance series."""
    column = SECTOR_BALANCE_PCT_GDP[sector]
    row = breaks.loc[breaks["sector"].eq(sector) & breaks["regime"].eq(regime)].iloc[0]
    start, end = (int(value) for value in str(regime).split("_")[0].split("-"))
    frame = panel.loc[panel["year"].between(start, end), ["year", column]].dropna().sort_values("year")
    label = SECTOR_LABELS[sector]
    fig, ax = _panel(
        title=f"Piecewise-constant mean model: {label}, {start}-{end}",
        ylabel="% GDP",
        height=4.2,
    )
    ax.plot(
        frame["year"],
        frame[column],
        color=SECTOR_COLOURS[sector],
        label=f"{label} balance",
        zorder=3,
    )
    break_years = [int(value) for value in str(row["break_years"]).split(";") if value not in ("", "nan")]
    means = [float(value) for value in str(row["segment_means_pct_gdp"]).split(";")]
    boundaries = [start, *break_years, end + 1]
    for index, mean in enumerate(means):
        if index == 0:
            ax.hlines(
                mean,
                boundaries[index] - 0.5,
                boundaries[index + 1] - 0.5,
                color=INK_PRIMARY,
                linewidth=1.8,
                zorder=4,
                label="Segment mean",
            )
        else:
            ax.hlines(
                mean,
                boundaries[index] - 0.5,
                boundaries[index + 1] - 0.5,
                color=INK_PRIMARY,
                linewidth=1.8,
                zorder=4,
            )
    for year in break_years:
        ax.axvline(year - 0.5, color=INK_MUTED, linewidth=1.0, zorder=1)
        ax.annotate(
            str(year),
            xy=(year - 0.5, 0.02),
            xycoords=("data", "axes fraction"),
            xytext=(4, 0),
            textcoords="offset points",
            fontsize=8.5,
            color=INK_MUTED,
        )
    _zero_rule(ax)
    _legend(ax)
    return fig


def social_security_composition(ssf: pd.DataFrame) -> Figure:
    """Plot Social Security Funds revenue, expenditure and contributions as GDP shares."""
    frame = ssf.sort_values("year")
    fig, ax = _panel(
        title="Social Security Funds: revenue, contributions and expenditure",
        ylabel="% GDP",
    )
    anchors = [
        _line(ax, frame, "revenue_pct_gdp", label="Total revenue", colour=SERIES_COLOURS[0]),
        _line(ax, frame, "expenditure_pct_gdp", label="Total expenditure", colour=SERIES_COLOURS[1]),
        _line(ax, frame, "contributions_pct_gdp", label="Social contributions", colour=SERIES_COLOURS[2]),
    ]
    _splice_marker(ax)
    _legend(ax, ncol=3)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def social_security_contribution_share(ssf: pd.DataFrame) -> Figure:
    """Plot the share of Social Security Funds revenue coming from contributions."""
    frame = ssf.dropna(subset=["contributions_share_total_revenue"]).sort_values("year")
    fig, ax = _panel(
        title="Social contributions as a share of total Social Security Funds revenue",
        ylabel="% of total SSF revenue",
        height=4.2,
    )
    years, values = _gap_aware(frame, "contributions_share_total_revenue")
    ax.plot(
        years,
        100.0 * values,
        color=SECTOR_COLOURS["social_security_funds"],
        marker="o",
        markeredgecolor=SURFACE,
        markeredgewidth=1.2,
        label="Contribution share",
        zorder=3,
    )
    _splice_marker(ax)
    _legend(ax)
    return fig


def social_security_systems(systems: pd.DataFrame) -> Figure:
    """Plot the CFP internal Social Security system balances."""
    frame = systems.sort_values("year")
    fig, ax = _panel(
        title="CFP Social Security budget systems: internal balances",
        ylabel="Million euro",
        height=4.2,
    )
    _signed_stack(
        ax,
        frame["year"].to_numpy(dtype=float),
        [
            (
                "Previdential system",
                frame["previdential_system_balance_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[0],
            ),
            (
                "Citizenship system",
                frame["citizenship_system_balance_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[1],
            ),
            (
                "Special regimes",
                frame["special_regimes_balance_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[2],
            ),
        ],
    )
    _zero_rule(ax)
    _legend(ax, ncol=3)
    return fig


def ssf_balance_change_decomposition(
    decomposition: pd.DataFrame,
    *,
    start_year: int,
    end_year: int,
) -> Figure:
    """Stack the account movements that compose each annual Social Security balance change.

    Every layer is a *contribution to the balance change*, so expenditure layers
    already carry their negative sign: a rise in social transfers appears below
    zero because it reduces the balance. Plotting the raw expenditure change here
    would put a bar above zero for a movement that worsened the balance, which is
    the ambiguity this figure exists to remove.
    """
    frame = decomposition.loc[
        decomposition["year"].between(start_year, end_year)
    ].sort_values("year")
    fig, ax = _panel(
        title=(
            "Contributions to the annual change in the Social Security balance, "
            f"{start_year}-{end_year}"
        ),
        ylabel="Contribution to the balance change, million euro",
        height=5.0,
    )
    _signed_stack(
        ax,
        frame["year"].to_numpy(dtype=float),
        [
            (
                "Social contributions",
                frame["contributions_contribution_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[2],
            ),
            (
                "Other revenue",
                frame["other_revenue_contribution_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[0],
            ),
            (
                "Social transfers paid",
                frame["social_transfers_contribution_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[1],
            ),
            (
                "Other expenditure",
                frame["other_expenditure_contribution_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[4],
            ),
        ],
    )
    ax.plot(
        frame["year"],
        frame["balance_change_m_eur"],
        color=INK_PRIMARY,
        linewidth=1.6,
        label="Change in balance (identity total)",
        zorder=4,
    )
    _zero_rule(ax)
    ax.annotate(
        "Expenditure layers carry the sign with which they enter the balance",
        xy=(0.006, 0.02),
        xycoords="axes fraction",
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=INK_MUTED,
    )
    _legend(ax, ncol=3)
    return fig


def ssf_accounting_boundary(comparison: pd.DataFrame) -> Figure:
    """Contrast the ESA 2010 Social Security balance with the budget-system total.

    Two stacked panels are used on purpose. The top panel carries the two balances
    on a shared axis, where they look almost identical; the bottom panel carries
    the difference on its own axis, which is the quantity of interest and would be
    invisible at the scale of the levels. Plotting the difference as a third line
    in the top panel would hide exactly what the figure exists to show.
    """
    apply_house_style()
    frame = comparison.sort_values("year")
    fig, axes = plt.subplots(2, 1, figsize=(10.0, 5.8), sharex=True)
    top, bottom = axes[0], axes[1]
    # The legend sits above this panel, so the title needs the same clearance the
    # single-panel helper gives it.
    top.set_title(
        "Two accounting boundaries for Social Security: national accounts and budget systems",
        pad=30.0,
    )
    top.plot(
        frame["year"],
        frame["esa2010_ssf_balance_m_eur"],
        color=SECTOR_COLOURS["social_security_funds"],
        marker="o",
        markeredgecolor=SURFACE,
        markeredgewidth=1.2,
        label="ESA 2010 Social Security Funds balance",
        zorder=3,
    )
    top.plot(
        frame["year"],
        frame["budget_system_total_m_eur"],
        color=SERIES_COLOURS[0],
        marker="s",
        markeredgecolor=SURFACE,
        markeredgewidth=1.2,
        label="CFP budget-system total",
        zorder=3,
    )
    top.set_ylabel("Million euro")
    top.axhline(0.0, color=BASELINE, linewidth=1.0, zorder=1)
    _legend(top, ncol=2)
    bottom.bar(
        frame["year"].to_numpy(dtype=float),
        frame["boundary_difference_m_eur"].to_numpy(dtype=float),
        width=0.6,
        color=SERIES_COLOURS[1],
        edgecolor=SURFACE,
        linewidth=1.2,
        zorder=2,
    )
    bottom.set_ylabel("Difference, million euro")
    bottom.set_xlabel("Year")
    bottom.axhline(0.0, color=BASELINE, linewidth=1.0, zorder=1)
    bottom.xaxis.set_major_locator(MaxNLocator(integer=True))
    bottom.annotate(
        "National accounts minus budget systems: never zero, never added together",
        xy=(0.006, 0.94),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=8.5,
        color=INK_MUTED,
    )
    for ax in axes:
        ax.grid(visible=True, axis="y")
        ax.set_axisbelow(True)
    return fig


def primary_vs_headline(primary: pd.DataFrame, sector: str) -> Figure:
    """Plot the headline balance, the primary balance and interest for one sector."""
    frame = primary.loc[primary["sector"].eq(sector)].sort_values("year").copy()
    frame["headline_pct_gdp"] = 100.0 * frame["balance_m_eur"] / frame["nominal_gdp_m_eur"]
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=f"Headline balance, primary balance and interest: {label}",
        ylabel="% GDP",
    )
    anchors = [
        _line(ax, frame, "headline_pct_gdp", label="Headline balance", colour=SERIES_COLOURS[0]),
        _line(ax, frame, "primary_balance_pct_gdp", label="Primary balance", colour=SERIES_COLOURS[1]),
        _line(ax, frame, "interest_pct_gdp", label="Interest expenditure", colour=SERIES_COLOURS[2]),
    ]
    _zero_rule(ax)
    _splice_marker(ax)
    _legend(ax, ncol=3)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def interest_burden(primary: pd.DataFrame) -> Figure:
    """Compare interest expenditure across sectors as a share of GDP."""
    fig, ax = _panel(title="Interest expenditure by sector", ylabel="% GDP")
    anchors = []
    for sector in SECTOR_BALANCE_PCT_GDP:
        frame = primary.loc[primary["sector"].eq(sector)].sort_values("year")
        if frame.empty:
            continue
        anchors.append(
            _line(
                ax,
                frame,
                "interest_pct_gdp",
                label=SECTOR_LABELS[sector],
                colour=SECTOR_COLOURS[sector],
            )
        )
    _splice_marker(ax)
    _legend(ax, ncol=2)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def investment_diagnostic(investment: pd.DataFrame, sector: str) -> Figure:
    """Plot the balance, GFCF and the non-official balance before GFCF."""
    frame = investment.loc[investment["sector"].eq(sector)].sort_values("year").copy()
    frame["balance_pct_gdp"] = 100.0 * frame["balance_m_eur"] / frame["nominal_gdp_m_eur"]
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=f"Balance, GFCF and the diagnostic balance before GFCF: {label}",
        ylabel="% GDP",
    )
    anchors = [
        _line(ax, frame, "balance_pct_gdp", label="Balance (B.9)", colour=SERIES_COLOURS[0]),
        _line(ax, frame, "gfcf_pct_gdp", label="GFCF", colour=SERIES_COLOURS[1]),
        _line(
            ax,
            frame,
            "balance_before_gfcf_pct_gdp",
            label="Balance before GFCF (diagnostic)",
            colour=SERIES_COLOURS[2],
        ),
    ]
    _zero_rule(ax)
    _splice_marker(ax)
    _legend(ax, ncol=3)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def gfcf_by_sector(investment: pd.DataFrame) -> Figure:
    """Compare gross fixed capital formation across sectors."""
    fig, ax = _panel(title="Gross fixed capital formation by sector", ylabel="% GDP")
    anchors = []
    for sector in SECTOR_BALANCE_PCT_GDP:
        frame = investment.loc[investment["sector"].eq(sector)].sort_values("year")
        if frame.empty:
            continue
        anchors.append(
            _line(
                ax,
                frame,
                "gfcf_pct_gdp",
                label=SECTOR_LABELS[sector],
                colour=SECTOR_COLOURS[sector],
            )
        )
    _splice_marker(ax)
    _legend(ax, ncol=2)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def debt_and_stock_flow(debt: pd.DataFrame, *, sector: str = "general_government") -> Figure:
    """Plot the Maastricht debt ratio and the stock-flow adjustment."""
    frame = debt.loc[debt["sector"].eq(sector)].sort_values("year")
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(title=f"Maastricht debt and stock-flow adjustment: {label}", ylabel="% GDP")
    anchors = [
        _line(ax, frame, "debt_pct_gdp", label="Debt", colour=SERIES_COLOURS[0]),
        _line(
            ax,
            frame,
            "stock_flow_adjustment_pct_gdp",
            label="Stock-flow adjustment",
            colour=SERIES_COLOURS[1],
        ),
    ]
    _zero_rule(ax)
    _legend(ax, ncol=2)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def debt_change_decomposition(debt: pd.DataFrame, *, sector: str = "general_government") -> Figure:
    """Decompose the annual debt change into minus the balance and the adjustment."""
    frame = debt.loc[debt["sector"].eq(sector)].sort_values("year")
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=f"Annual debt change decomposed: {label}",
        ylabel="Million euro",
        height=4.6,
    )
    _signed_stack(
        ax,
        frame["year"].to_numpy(dtype=float),
        [
            ("Minus the balance", -frame["balance_m_eur"].to_numpy(dtype=float), SERIES_COLOURS[0]),
            (
                "Stock-flow adjustment",
                frame["stock_flow_adjustment_m_eur"].to_numpy(dtype=float),
                SERIES_COLOURS[1],
            ),
        ],
    )
    ax.plot(
        frame["year"],
        frame["debt_change_m_eur"],
        color=INK_PRIMARY,
        linewidth=1.6,
        label="Change in debt (identity total)",
        zorder=4,
    )
    _zero_rule(ax)
    _legend(ax, ncol=3)
    return fig


def transfer_sensitivity(sensitivity: pd.DataFrame, sector: str) -> Figure:
    """Plot the recorded balance against the mechanical transfer-removal sensitivity."""
    frame = sensitivity.loc[sensitivity["sector"].eq(sector)].sort_values("year")
    label = SECTOR_LABELS.get(sector, sector.replace("_", " ").title())
    fig, ax = _panel(
        title=f"Mechanical intragovernmental-transfer sensitivity: {label}",
        ylabel="Million euro",
        height=4.2,
    )
    anchors = [
        _line(ax, frame, "balance_m_eur", label="Recorded balance", colour=SERIES_COLOURS[0]),
        _line(
            ax,
            frame,
            "balance_after_mechanical_transfer_removal_m_eur",
            label="After mechanical transfer removal",
            colour=SERIES_COLOURS[1],
        ),
        _line(
            ax,
            frame,
            "net_intragov_transfer_m_eur",
            label="Net transfer received",
            colour=SERIES_COLOURS[2],
        ),
    ]
    _zero_rule(ax)
    _legend(ax)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def nominal_growth_scatter(macro: pd.DataFrame, *, sector: str = "general_government") -> Figure:
    """Scatter a balance ratio against nominal GDP growth, split by statistical regime."""
    column = SECTOR_BALANCE_PCT_GDP[sector]
    frame = macro[["year", "nominal_gdp_growth", "modern_regime", column]].dropna()
    label = SECTOR_LABELS[sector]
    fig, ax = _panel(
        title=f"{label} balance against nominal GDP growth",
        ylabel="% GDP",
        xlabel="Nominal GDP growth",
        height=4.4,
        grid_axis="both",
    )
    for regime, regime_label, colour in (
        (0, "Historical regime, 1977-1994", SERIES_COLOURS[0]),
        (1, "Modern regime, 1995-2025", SERIES_COLOURS[1]),
    ):
        subset = frame.loc[frame["modern_regime"].eq(regime)]
        ax.scatter(
            subset["nominal_gdp_growth"],
            subset[column],
            s=44,
            color=colour,
            edgecolor=SURFACE,
            linewidth=1.2,
            label=regime_label,
            zorder=3,
        )
    _zero_rule(ax)
    ax.axvline(0.0, color=BASELINE, linewidth=1.0, zorder=1)
    _legend(ax)
    return fig


def historical_labour_context(macro: pd.DataFrame, *, end_year: int = 1995) -> Figure:
    """Show the SSF balance beside the historical labour-market series.

    Two stacked panels are used rather than a second y-axis: aligning two
    different scales on one axis would imply a relationship the data do not
    contain.
    """
    apply_house_style()
    frame = macro.loc[macro["year"].le(end_year)].sort_values("year")
    fig, axes = plt.subplots(2, 1, figsize=(10.0, 5.8), sharex=True)
    top, bottom = axes[0], axes[1]
    top.set_title(
        f"Social Security Funds balance and labour market, 1977-{end_year}",
        pad=12.0,
    )
    top.plot(
        frame["year"],
        frame["social_security_balance_pct_gdp"],
        color=SECTOR_COLOURS["social_security_funds"],
        label="SSF balance",
        zorder=3,
    )
    top.set_ylabel("SSF balance, % GDP")
    top.axhline(0.0, color=BASELINE, linewidth=1.0, zorder=1)
    bottom.plot(
        frame["year"],
        100.0 * frame["unemployment_rate"],
        color=SERIES_COLOURS[0],
        label="Unemployment rate",
        zorder=3,
    )
    bottom.plot(
        frame["year"],
        100.0 * frame["employment_growth"],
        color=SERIES_COLOURS[1],
        label="Employment growth",
        zorder=3,
    )
    bottom.axhline(0.0, color=BASELINE, linewidth=1.0, zorder=1)
    bottom.set_ylabel("Percent")
    bottom.set_xlabel("Year")
    bottom.xaxis.set_major_locator(MaxNLocator(integer=True))
    _legend(bottom, ncol=2)
    for ax in axes:
        ax.grid(visible=True, axis="y")
        ax.set_axisbelow(True)
    return fig


def source_overlap_1995(overlap: pd.DataFrame) -> Figure:
    """Plot the 1995 revision between the two retained balance vintages.

    The levels themselves differ by far more than the revision, so plotting the
    levels side by side would hide the quantity of interest. The revision is
    shown here and both vintages stay visible in the accompanying table.
    """
    frame = overlap.copy()
    frame["label"] = frame["metric"].map(METRIC_LABELS).fillna(frame["metric"])
    fig, ax = _panel(
        title="1995 overlap: modern vintage minus historical vintage",
        ylabel="Revision, million euro",
        xlabel="",
        height=4.2,
    )
    differences = frame["difference_m_eur"].to_numpy(dtype=float)
    ax.bar(
        np.arange(len(frame), dtype=float),
        differences,
        width=0.42,
        color=[POSITIVE_COLOUR if value >= 0.0 else NEGATIVE_COLOUR for value in differences],
        edgecolor=SURFACE,
        linewidth=1.2,
        zorder=2,
    )
    ax.set_xticks(np.arange(len(frame), dtype=float), frame["label"].tolist())
    ax.legend(
        handles=[
            Patch(facecolor=POSITIVE_COLOUR, label="Modern vintage higher"),
            Patch(facecolor=NEGATIVE_COLOUR, label="Modern vintage lower"),
        ],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        borderaxespad=0.0,
        ncol=2,
    )
    _zero_rule(ax)
    return fig


def modern_source_differences(comparison: pd.DataFrame) -> Figure:
    """Plot the difference between the PORDATA bridge and the CFP workbooks."""
    frame = comparison.sort_values("year")
    fig, ax = _panel(
        title="PORDATA bridge minus CFP ESA 2010 workbook, by subsector",
        ylabel="Difference, million euro",
    )
    anchors = []
    for sector, column in (
        ("general_government", "general_government_source_difference_m_eur"),
        ("central_government", "central_government_source_difference_m_eur"),
        ("regional_local_government", "regional_local_source_difference_m_eur"),
        ("social_security_funds", "social_security_source_difference_m_eur"),
    ):
        anchors.append(
            _line(
                ax,
                frame.dropna(subset=[column]),
                column,
                label=SECTOR_LABELS[sector],
                colour=SECTOR_COLOURS[sector],
            )
        )
    _zero_rule(ax)
    _legend(ax, ncol=2)
    _end_labels(ax, [anchor for anchor in anchors if anchor is not None])
    return fig


def account_coverage(accounts: pd.DataFrame) -> Figure:
    """Show which sector-years have detailed account components, and which do not."""
    apply_house_style()
    sectors = list(SECTOR_BALANCE_PCT_GDP)
    fig, ax = plt.subplots(figsize=(10.0, 3.2))
    ax.set_title("Detailed account coverage: the 1996-1999 subsector gap is not imputed", pad=30.0)
    for index, sector in enumerate(sectors):
        frame = accounts.loc[accounts["sector"].eq(sector)]
        for regime, colour in REGIME_COLOURS.items():
            subset = frame.loc[frame["statistical_regime"].eq(regime)]
            ax.scatter(
                subset["year"],
                np.full(len(subset), index, dtype=float),
                s=26,
                marker="s",
                color=colour,
                edgecolor=SURFACE,
                linewidth=0.8,
                zorder=3,
            )
    ax.set_yticks(range(len(sectors)), [SECTOR_LABELS[sector] for sector in sectors])
    ax.invert_yaxis()
    ax.set_xlabel("Year")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(visible=True, axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelcolor=INK_SECONDARY)
    ax.legend(
        handles=[
            Patch(facecolor=colour, label=REGIME_LABELS[regime])
            for regime, colour in REGIME_COLOURS.items()
        ],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.0),
        borderaxespad=0.0,
        ncol=2,
    )
    return fig


def european_benchmark(summary: pd.DataFrame, *, highlight: str = "PT") -> Figure:
    """Place one country in the cross-country distribution of two sign frequencies.

    A single-country study can say how Portugal behaves; only a distribution can say
    whether that is unusual. The two frequencies plotted are the ones the domestic
    analysis found most persistent, so this figure answers the question the rest of
    the analysis raises but cannot settle.

    Countries are ordered by the Social Security frequency rather than
    alphabetically, because the position in the ranking is the quantity of interest.
    """
    frame = summary.sort_values("share_ssf_positive").reset_index(drop=True)
    positions = np.arange(len(frame), dtype=float)
    is_target = frame["country"].eq(highlight).to_numpy()

    apply_house_style()
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 5.6), sharey=True)
    left, right = axes[0], axes[1]
    for ax, column, title in (
        (left, "share_ssf_positive", "Years with a Social Security surplus"),
        (right, "share_central_negative", "Years with a Central Government deficit"),
    ):
        colours = [
            SECTOR_COLOURS["social_security_funds"] if flag else NEUTRAL_COLOUR
            for flag in is_target
        ]
        edges = [INK_PRIMARY if flag else BASELINE for flag in is_target]
        ax.barh(
            positions,
            100.0 * frame[column].to_numpy(dtype=float),
            color=colours,
            edgecolor=edges,
            linewidth=1.0,
            zorder=2,
        )
        ax.set_title(title, pad=10.0, fontsize=10.5)
        ax.set_xlabel("Share of reported years, %")
        ax.grid(visible=True, axis="x")
        ax.set_axisbelow(True)
        ax.set_xlim(0, 100)

    left.set_yticks(positions, frame["country"].tolist())
    left.tick_params(axis="y", length=0, labelcolor=INK_SECONDARY)
    left.set_ylim(-0.8, len(frame) - 0.2)
    fig.suptitle(
        f"Subsector sign frequencies across reporters, {highlight} highlighted",
        x=0.01,
        ha="left",
        fontsize=12.5,
        color=INK_PRIMARY,
    )
    return fig


def european_offset_distribution(panel: pd.DataFrame, *, highlight: str = "PT") -> Figure:
    """Compare one country's offset ratios with the pooled cross-country distribution.

    Only country-years in which the ratio is defined appear, so the horizontal
    position is comparable across countries; the counts differ and are stated in the
    caption rather than implied by the widths.
    """
    defined = panel.dropna(subset=["offset_ratio"])
    target = defined.loc[defined["country"].eq(highlight), "offset_ratio"]
    others = defined.loc[~defined["country"].eq(highlight), "offset_ratio"]

    fig, ax = _panel(
        title="Offset ratio where defined: one country against all other reporters",
        ylabel="Share of country-years, %",
        xlabel="Social Security balance / |non-Social-Security balance|",
        height=4.6,
        grid_axis="y",
    )
    edges = np.linspace(0.0, 3.0, 25).tolist()
    for values, label, colour in (
        (others, "All other reporters", SERIES_COLOURS[0]),
        (target, f"{highlight}", SECTOR_COLOURS["social_security_funds"]),
    ):
        clipped = values.clip(upper=edges[-1])
        weights = np.full(len(clipped), 100.0 / max(len(clipped), 1))
        ax.hist(
            clipped,
            bins=edges,
            weights=weights,
            histtype="stepfilled",
            alpha=0.55,
            color=colour,
            edgecolor=colour,
            linewidth=1.4,
            label=label,
            zorder=3,
        )
    _reference_rule(ax, 0.0, "")
    ax.axvline(1.0, color=INK_MUTED, linewidth=1.0, zorder=1)
    ax.annotate(
        "ratio = 1",
        xy=(1.0, 0.96),
        xycoords=("data", "axes fraction"),
        xytext=(4, 0),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8.5,
        color=INK_MUTED,
    )
    _legend(ax, ncol=2)
    return fig


def closure_errors(panel: pd.DataFrame, *, tolerance_m_eur: float = 2.0) -> Figure:
    """Plot the subsector closure residual against its tolerance band."""
    frame = panel.sort_values("year")
    fig, ax = _panel(
        title="Subsector closure residual of the core accounting identity",
        ylabel="Residual, million euro",
        height=3.8,
    )
    ax.axhspan(
        -tolerance_m_eur,
        tolerance_m_eur,
        color=NEUTRAL_COLOUR,
        zorder=1,
        label=f"Tolerance band, +/-{tolerance_m_eur:g} M EUR",
    )
    ax.bar(
        frame["year"],
        frame["closure_error_m_eur"],
        width=0.74,
        color=SERIES_COLOURS[0],
        edgecolor=SURFACE,
        linewidth=1.2,
        label="Closure residual",
        zorder=2,
    )
    _zero_rule(ax)
    _legend(ax, ncol=2)
    return fig
