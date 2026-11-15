"""Is the shift after Terra about the event, or about the market a DApp launches into?

Same fit as coef_by_period.py, but DApps are grouped by market growth at launch instead of by date:
launch_eco_growth_3m (the team's feature: active wallets in the launch month vs 3 months earlier), split at its
median into faster and slower growth. The slower half is not only shrinking markets; it also holds slow growth,
since only 104 DApps (13 successful) launch into a shrinking market, too few to fit 26 coefficients.
The split feature itself is left out of the fit. DApps launched before the feature has 3 months of history are dropped.

Faster growth is mostly 2020-21 and slower growth mostly 2022-24, so the split is repeated on 2023-24 launches alone,
the only years with enough DApps on both sides, with the same median: time is then about the same for both halves.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import TARGET, record
from coef_by_period import fit_with_resamples
from features import FEATURE_COLS

REGIME = "launch_eco_growth_3m"
FEATURES = [f for f in FEATURE_COLS if f != REGIME]
SAME_YEARS = [2023, 2024]
SEED = 42


def regimes(growth: pd.Series, median: float) -> dict[str, pd.Series]:
    return {"Faster growth": growth > median, "Slower growth": growth <= median}


def run(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df[REGIME].notna()].reset_index(drop=True)
    median = df[REGIME].median()

    # Market growth at each launch month (every DApp launched that month has the same value)
    months = df.groupby("launch_month").agg(growth=(REGIME, "first"), n_dapps=(TARGET, "size"),
                                            n_successful=(TARGET, "sum")).reset_index()
    record(months.assign(faster=months["growth"] > median, median_growth=median), "market_growth_by_month")

    samples = {"All launches": df,
               "2023-24 launches": df[df["launch_month"].dt.year.isin(SAME_YEARS)].reset_index(drop=True)}
    rng = np.random.default_rng(SEED)
    feature_rows, group_rows, sizes = [], [], []
    for sample, s in samples.items():
        for name, mask in regimes(s[REGIME], median).items():
            d = s[mask].reset_index(drop=True)
            f_rows, g_rows = fit_with_resamples(d, "regime", name, rng, FEATURES)
            feature_rows += [{"sample": sample, **r} for r in f_rows]
            group_rows += [{"sample": sample, **r} for r in g_rows]
            # Launch years and months in each half, to show how far market growth and time overlap
            years = d["launch_month"].dt.year.value_counts().sort_index()
            sizes.append({"sample": sample, "regime": name, "median_growth": median, "n_dapps": len(d),
                          "n_successful": int(d[TARGET].sum()), "n_launch_months": d["launch_month"].nunique(),
                          "n_shrinking": int((d[REGIME] <= 0).sum()),
                          **{f"launched_{y}": int(n) for y, n in years.items()}})
    sizes = pd.DataFrame(sizes)
    years = sorted(c for c in sizes if c.startswith("launched_"))
    sizes[years] = sizes[years].fillna(0).astype(int)
    record(sizes[[c for c in sizes if c not in years] + years], "regime_sizes")
    record(pd.DataFrame(feature_rows), "coef_by_regime")
    return record(pd.DataFrame(group_rows), "coef_groups_by_regime")
