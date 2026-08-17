"""Conservative structural-break detection for annual balance ratios."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

BALANCE_SERIES = {
    "general_government": "general_government_balance_pct_gdp",
    "central_government": "central_government_balance_pct_gdp",
    "regional_local_government": "regional_local_balance_pct_gdp",
    "social_security_funds": "social_security_balance_pct_gdp",
}


def _segment_sse(y: np.ndarray, start: int, end: int) -> float:
    segment = y[start:end]
    if len(segment) == 0:
        return math.inf
    return float(np.square(segment - segment.mean()).sum())


def detect_mean_breaks(
    years: np.ndarray,
    values: np.ndarray,
    *,
    max_breaks: int = 2,
    min_segment: int = 5,
) -> dict[str, object]:
    """Select piecewise-constant mean breaks by dynamic programming and BIC.

    This intentionally modest model is appropriate for short annual series. It is not
    used across the known 1995 source splice; callers should analyse each statistical
    regime separately.
    """
    if years.ndim != 1 or values.ndim != 1 or len(years) != len(values):
        raise ValueError("years and values must be one-dimensional arrays of equal length")
    n = len(values)
    if n < 2 * min_segment:
        return {"n": n, "n_breaks": 0, "break_years": [], "bic": math.nan, "segment_means": [float(values.mean())]}

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
        rss = max(rss, 1e-12)
        # segment means + break locations are counted as free parameters.
        parameter_count = 2 * segments - 1
        bic = n * math.log(rss / n) + parameter_count * math.log(n)
        candidates.append((bic, segments))
    bic, selected_segments = min(candidates, key=lambda item: item[0])

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
    }


def structural_break_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Detect breaks separately inside the historical and modern statistical regimes."""
    records: list[dict[str, object]] = []
    regimes = {
        "1977-1994_historical": (1977, 1994),
        "1995-2025_modern": (1995, 2025),
    }
    for regime, (start, end) in regimes.items():
        sub = panel.loc[panel["year"].between(start, end)].sort_values("year")
        for sector, column in BALANCE_SERIES.items():
            clean = sub[["year", column]].dropna()
            result = detect_mean_breaks(
                clean["year"].to_numpy(dtype=int),
                clean[column].to_numpy(dtype=float),
                max_breaks=2,
                min_segment=5,
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
                }
            )
    return pd.DataFrame.from_records(records)
