"""Sensitivity calculations for intra-governmental transfers."""

from __future__ import annotations

import pandas as pd


def transfer_reallocation_sensitivity(accounts: pd.DataFrame, transfers: pd.DataFrame) -> pd.DataFrame:
    """Mechanically reallocate net intragovernmental transfers for sensitivity only.

    The result is not an alternative fiscal balance. It quantifies how the recorded
    location of a subsector balance changes under a purely mechanical transfer removal.
    """
    balances = accounts[["year", "sector", "balance_m_eur"]]
    frame = transfers.merge(balances, on=["year", "sector"], how="left", validate="one_to_one")
    frame["balance_after_mechanical_transfer_removal_m_eur"] = (
        frame["balance_m_eur"] - frame["net_intragov_transfer_m_eur"]
    )
    return frame.sort_values(["sector", "year"]).reset_index(drop=True)
