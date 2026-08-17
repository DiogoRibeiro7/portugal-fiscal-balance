"""Conservative structural-break detection for annual balance ratios."""

from __future__ import annotations

import math
from typing import TypedDict

import numpy as np
import pandas as pd

from portugal_fiscal_balance.schemas import SECTOR_BALANCE_PCT_GDP, STATISTICAL_REGIMES

BALANCE_SERIES = SECTOR_BALANCE_PCT_GDP

REGIMES = STATISTICAL_REGIMES

#: Minimum segment lengths swept by the sensitivity grid.
SENSITIVITY_MIN_SEGMENTS: tuple[int, ...] = (4, 5, 6, 7)

#: Maximum break counts swept by the sensitivity grid.
SENSITIVITY_MAX_BREAKS: tuple[int, ...] = (1, 2, 3)


class BreakResult(TypedDict):
    n: int
    n_breaks: int
    break_years: list[int]
    bic: float
    segment_means: list[float]
    #: BIC of every admissible break count, keyed by the number of breaks. The
    #: selected count is the arg-min; the spread across the ladder shows how
    #: decisively BIC preferred it, which a single selected date cannot convey.
    bic_by_n_breaks: dict[int, float]


def _segment_sse(y: np.ndarray, start: int, end: int) -> float:
    segment = y[start:end]
    if len(segment) == 0:
        return math.inf
    return float(np.square(segment - segment.mean()).sum())


def _bic(rss: float, n: int, *, segments: int) -> float:
    """BIC of a piecewise-constant fit with ``segments`` segments.

    Segment means and break locations are both counted as free parameters, which
    is the conservative choice: it penalises an extra break twice and therefore
    makes the model less willing to claim one.
    """
    parameter_count = 2 * segments - 1
    return n * math.log(max(rss, 1e-12) / n) + parameter_count * math.log(n)


def detect_mean_breaks(
    years: np.ndarray,
    values: np.ndarray,
    *,
    max_breaks: int = 2,
    min_segment: int = 5,
) -> BreakResult:
    """Select piecewise-constant mean breaks by dynamic programming and BIC.

    This intentionally modest model is appropriate for short annual series. It is not
    used across the known 1995 source splice; callers should analyse each statistical
    regime separately.
    """
    if years.ndim != 1 or values.ndim != 1 or len(years) != len(values):
        raise ValueError("years and values must be one-dimensional arrays of equal length")
    n = len(values)
    if n < 2 * min_segment:
        flat_bic = _bic(_segment_sse(values, 0, n), n, segments=1)
        return {
            "n": n,
            "n_breaks": 0,
            "break_years": [],
            "bic": flat_bic,
            "segment_means": [float(values.mean())],
            "bic_by_n_breaks": {0: flat_bic},
        }

    max_segments = min(max_breaks + 1, n // min_segment)
    sse = np.full((n + 1, n + 1), np.inf)
    for start in range(n):
        for end in range(start + min_segment, n + 1):
            sse[start, end] = _segment_sse(values, start, end)

    dp = np.full((max_segments + 1, n + 1), np.inf)
    prev = np.full((max_segments + 1, n + 1), -1, dtype=int)
    for end in range(min_segment, n + 1):
        dp[1, end] = sse[0, end]

    for segments in range(2, max_segments + 1):
        min_end = segments * min_segment
        for end in range(min_end, n + 1):
            for split in range((segments - 1) * min_segment, end - min_segment + 1):
                cost = dp[segments - 1, split] + sse[split, end]
                if cost < dp[segments, end]:
                    dp[segments, end] = cost
                    prev[segments, end] = split

    candidates: list[tuple[float, int]] = []
    for segments in range(1, max_segments + 1):
        rss = float(dp[segments, n])
        if not math.isfinite(rss):
            continue
        candidates.append((_bic(rss, n, segments=segments), segments))
    bic, selected_segments = min(candidates, key=lambda item: item[0])
    ladder = {segments - 1: value for value, segments in candidates}

    boundaries = [n]
    end = n
    segments = selected_segments
    while segments > 1:
        split = int(prev[segments, end])
        boundaries.append(split)
        end = split
        segments -= 1
    boundaries.append(0)
    boundaries = sorted(boundaries)
    break_indexes = boundaries[1:-1]
    break_years = [int(years[index]) for index in break_indexes]
    means = [float(values[start:end].mean()) for start, end in zip(boundaries[:-1], boundaries[1:], strict=True)]
    return {
        "n": n,
        "n_breaks": selected_segments - 1,
        "break_years": break_years,
        "bic": float(bic),
        "segment_means": means,
        "bic_by_n_breaks": ladder,
    }


def _regime_series(panel: pd.DataFrame) -> list[tuple[str, str, np.ndarray, np.ndarray]]:
    """Yield the clean year/value arrays for every regime-sector combination."""
    series: list[tuple[str, str, np.ndarray, np.ndarray]] = []
    for regime, (start, end) in REGIMES.items():
        sub = panel.loc[panel["year"].between(start, end)].sort_values("year")
        for sector, column in BALANCE_SERIES.items():
            clean = sub[["year", column]].dropna()
            series.append(
                (
                    regime,
                    sector,
                    clean["year"].to_numpy(dtype=int),
                    clean[column].to_numpy(dtype=float),
                )
            )
    return series


def structural_break_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Detect breaks separately inside the historical and modern statistical regimes."""
    records: list[dict[str, object]] = []
    for regime, sector, years, values in _regime_series(panel):
        result = detect_mean_breaks(years, values, max_breaks=2, min_segment=5)
        ladder = result["bic_by_n_breaks"]
        best = result["bic"]
        runner_up = sorted(
            value for count, value in ladder.items() if count != result["n_breaks"]
        )
        records.append(
            {
                "regime": regime,
                "sector": sector,
                "n": result["n"],
                "n_breaks": result["n_breaks"],
                "break_years": ";".join(str(v) for v in result["break_years"]),
                "segment_means_pct_gdp": ";".join(f"{v:.4f}" for v in result["segment_means"]),
                "bic": result["bic"],
                # How much better than the next-best break count the selection is.
                # A small margin means the date should not be read as determined.
                "bic_margin_over_next_best": (
                    float(runner_up[0] - best) if runner_up else math.nan
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def structural_break_bic_ladder(panel: pd.DataFrame) -> pd.DataFrame:
    """Report the BIC of every admissible break count under the preferred specification.

    Publishing only the selected break count hides how close the alternatives
    were. With eighteen or thirty-one annual observations the differences are
    often small, and a reader cannot judge that from the selected dates alone.
    """
    records: list[dict[str, object]] = []
    for regime, sector, years, values in _regime_series(panel):
        result = detect_mean_breaks(years, values, max_breaks=2, min_segment=5)
        best = min(result["bic_by_n_breaks"].values())
        for n_breaks, bic in sorted(result["bic_by_n_breaks"].items()):
            records.append(
                {
                    "regime": regime,
                    "sector": sector,
                    "n": result["n"],
                    "n_breaks": n_breaks,
                    "bic": bic,
                    "delta_bic_vs_best": float(bic - best),
                    "selected": bool(n_breaks == result["n_breaks"]),
                }
            )
    return pd.DataFrame.from_records(records)


def structural_break_sensitivity(
    panel: pd.DataFrame,
    *,
    min_segments: tuple[int, ...] = SENSITIVITY_MIN_SEGMENTS,
    max_breaks_grid: tuple[int, ...] = SENSITIVITY_MAX_BREAKS,
) -> pd.DataFrame:
    """Re-run detection across a grid of tuning choices.

    The two tuning parameters are not estimated from the data, so a date that
    only survives one of their values is an artefact of that choice rather than a
    feature of the series. The grid makes that visible instead of leaving the
    reader to trust a single specification.
    """
    records: list[dict[str, object]] = []
    for regime, sector, years, values in _regime_series(panel):
        for min_segment in min_segments:
            for max_breaks in max_breaks_grid:
                result = detect_mean_breaks(
                    years, values, max_breaks=max_breaks, min_segment=min_segment
                )
                records.append(
                    {
                        "regime": regime,
                        "sector": sector,
                        "n": result["n"],
                        "min_segment": min_segment,
                        "max_breaks": max_breaks,
                        "n_breaks": result["n_breaks"],
                        "break_years": ";".join(str(v) for v in result["break_years"]),
                        "bic": result["bic"],
                    }
                )
    return pd.DataFrame.from_records(records)


def structural_break_stability(sensitivity: pd.DataFrame) -> pd.DataFrame:
    """Summarise how often the sensitivity grid agrees on a break count and dates.

    ``modal_break_years_share`` is the fraction of grid cells returning exactly
    the modal set of dates. It is the quantity that decides whether a date can be
    stated as detected or only as a candidate.
    """
    records: list[dict[str, object]] = []
    for (regime, sector), group in sensitivity.groupby(["regime", "sector"], sort=False):
        counts = group["n_breaks"].value_counts()
        modal_count = int(counts.idxmax())
        year_sets = group["break_years"].fillna("").value_counts()
        modal_years = str(year_sets.idxmax())
        records.append(
            {
                "regime": regime,
                "sector": sector,
                "n_specifications": int(len(group)),
                "modal_n_breaks": modal_count,
                "modal_n_breaks_share": float(counts.max() / len(group)),
                "min_n_breaks": int(group["n_breaks"].min()),
                "max_n_breaks": int(group["n_breaks"].max()),
                "modal_break_years": modal_years,
                "modal_break_years_share": float(year_sets.max() / len(group)),
                "n_distinct_break_year_sets": int(len(year_sets)),
            }
        )
    return pd.DataFrame.from_records(records)
