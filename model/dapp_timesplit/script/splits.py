"""Train/test splits by launch month, with and without an embargo on the training answers.

Embargo rule: a training DApp's answer must be known before the test period starts,
    launch_month + 12 months < test start.
Test DApps are not embargoed: they are the future being predicted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import EVENTS, HOLDOUT_START, OUTCOME_LAG_MONTHS, TARGET


def answer_month(launch: pd.Series) -> pd.Series:
    """Last month of the outcome window (month 12, counted from 0)."""
    return launch + pd.DateOffset(months=OUTCOME_LAG_MONTHS)


def define_splits(df: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Each split is a (train mask, test mask) over the eligible DApps."""
    launch = df["launch_month"]
    known = answer_month(launch)
    terra, dencun = EVENTS["Terra"], EVENTS["Dencun"]
    return {
        # The team's split: by launch year only, so 2022 launches train on answers from 2023
        "current": (df["launch_year"] <= 2022, df["launch_year"].isin([2023, 2024])),
        # Same test, training answers known before 2023-01 (launches up to 2021-12)
        "leakage_fixed": (known < HOLDOUT_START, df["launch_year"].isin([2023, 2024])),
        # Event rounds: stand at the event (round 1 at Terra, round 2 at Dencun), train on answers known by then,
        # test on what launches next
        "round_1": (known < terra, (launch >= terra) & (launch < dencun)),
        "round_2": (known < dencun, launch >= dencun),
    }


def assignment(df: pd.DataFrame, splits: dict) -> pd.DataFrame:
    """Role of each DApp in each split: train, test, or unused."""
    out = df[["slug", "launch_month", TARGET]].copy()
    out["answer_known"] = answer_month(df["launch_month"])
    for name, (train, test) in splits.items():
        out[name] = np.select([train.to_numpy(), test.to_numpy()], ["train", "test"], "unused")
    return out
