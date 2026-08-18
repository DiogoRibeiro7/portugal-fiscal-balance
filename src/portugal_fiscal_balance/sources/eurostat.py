"""Eurostat government finance statistics, used only for the European benchmark.

The rest of this repository studies one country from national sources. This module
adds the one thing a single-country study cannot supply: whether the composition
documented for Portugal is unusual or ordinary among comparable reporters.

The file is the SDMX-CSV response of the dissemination API, retained exactly as
returned, flags included. Nothing is fetched at run time: the analysis reads the
bundled snapshot so a rebuild cannot silently pick up a later vintage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

#: ESA 2010 sector codes mapped to the names used throughout the repository.
SECTOR_CODES: Final[dict[str, str]] = {
    "S13": "general_government",
    "S1311": "central_government",
    "S1312": "state_government",
    "S1313": "local_government",
    "S1314": "social_security_funds",
}

#: Units retained. Ratios are computed in national currency because the published
#: percentage-of-GDP figures carry one decimal, which is too coarse a denominator
#: for a ratio: a non-Social-Security balance printed as -0.2 could be anywhere in
#: a band wide enough to move the ratio by a quarter of its value.
UNIT_COLUMNS: Final[dict[str, str]] = {
    "MIO_NAC": "balance_mio_nac",
    "PC_GDP": "balance_pct_gdp",
}

#: Reporters that are aggregates rather than countries. Keeping them in a
#: cross-country distribution would count the euro area as a peer of its members.
AGGREGATE_GEOS: Final[frozenset[str]] = frozenset(
    {"EA", "EA12", "EA19", "EA20", "EA21", "EU", "EU27_2020", "EU28"}
)


def extract_subsector_balances(path: Path) -> pd.DataFrame:
    """Read the bundled Eurostat snapshot into a long country-year-sector panel.

    Observation flags are preserved rather than dropped. Eurostat marks values as
    provisional (``p``), break-in-series (``b``) or missing (``m``), and a
    benchmark that silently discarded that information would present provisional
    figures from thirty countries as settled.
    """
    frame = pd.read_csv(path)
    required = ["unit", "sector", "geo", "TIME_PERIOD", "OBS_VALUE"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Eurostat snapshot is missing columns: {missing}")

    frame = frame.loc[frame["sector"].isin(SECTOR_CODES)]
    frame = frame.loc[~frame["geo"].isin(AGGREGATE_GEOS)]
    frame = frame.loc[frame["unit"].isin(UNIT_COLUMNS)]

    long = frame.rename(columns={"geo": "country", "TIME_PERIOD": "year"}).copy()
    long["sector"] = long["sector"].map(SECTOR_CODES).astype("string")
    long["year"] = long["year"].astype(int)
    long["flag"] = long.get("OBS_FLAG", pd.Series(index=long.index, dtype="object"))

    wide = long.pivot_table(
        index=["country", "year", "sector"],
        columns="unit",
        values="OBS_VALUE",
    ).reset_index()
    wide = wide.rename(columns=UNIT_COLUMNS)
    for column in UNIT_COLUMNS.values():
        if column not in wide.columns:
            wide[column] = pd.NA

    # One flag per country-year-sector: the same observation carries the same flag
    # in both units, so the first non-null is the observation's flag.
    flags = (
        long.dropna(subset=["flag"])
        .groupby(["country", "year", "sector"], as_index=False)["flag"]
        .first()
    )
    wide = wide.merge(flags, on=["country", "year", "sector"], how="left")

    ordered = ["country", "year", "sector", "balance_mio_nac", "balance_pct_gdp", "flag"]
    return wide[ordered].sort_values(["country", "year", "sector"]).reset_index(drop=True)


#: National-accounts items used to build the Social Security contribution base.
#: These are the Portuguese national accounts compiled by Statistics Portugal (INE)
#: and disseminated through Eurostat, which is why they are read here rather than
#: from a second national source: the API is versioned, stable and already used.
CONTRIBUTION_BASE_ITEMS: Final[dict[str, str]] = {
    "D11": "wages_and_salaries_m_eur",
    "D1": "compensation_of_employees_m_eur",
    "SAL_DC": "employees_k",
    "EMP_DC": "employment_k",
}


def extract_contribution_base(wage_path: Path, employment_path: Path) -> pd.DataFrame:
    """Read the wage-bill and employment snapshots into one annual panel.

    Two datasets are needed because Eurostat splits value and volume: the wage bill
    comes from the income side of the industry accounts and the head counts from the
    employment accounts. They share a dimension layout, so the parsing is common.
    """
    frames = []
    for path in (wage_path, employment_path):
        frame = pd.read_csv(path)
        required = ["na_item", "geo", "TIME_PERIOD", "OBS_VALUE"]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"{path.name} is missing columns: {missing}")
        frames.append(frame)

    long = pd.concat(frames, ignore_index=True)
    long = long.loc[long["na_item"].isin(CONTRIBUTION_BASE_ITEMS)]
    long = long.rename(columns={"TIME_PERIOD": "year"})
    long["year"] = long["year"].astype(int)

    wide = long.pivot_table(index="year", columns="na_item", values="OBS_VALUE").reset_index()
    wide = wide.rename(columns=CONTRIBUTION_BASE_ITEMS)
    for column in CONTRIBUTION_BASE_ITEMS.values():
        if column not in wide.columns:
            raise ValueError(f"Contribution-base panel is missing {column}")

    ordered = ["year", *CONTRIBUTION_BASE_ITEMS.values()]
    return wide[ordered].sort_values("year").reset_index(drop=True)
