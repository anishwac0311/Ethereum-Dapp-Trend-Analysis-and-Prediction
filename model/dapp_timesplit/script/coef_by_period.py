"""Which features drive success in each market period? Standardised logistic coefficients, fitted per period.

Same periods as size_effect.py, each fitted on its own with the team's L2 logistic regression on all 27 features.
Features are standardised first, so a coefficient is the change in log-odds of success for one standard deviation
more, and coefficients compare directly. Category is a 0/1 dummy rather than a standardised feature, so it is fitted
but left out of the rankings. Each period is resampled N_BOOT times, since after Dencun has only 12 successful DApps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import TARGET, record  # first: puts the team model on the import path
from features import (CAT_COLS, CONCENTRATION_FEATURES, CONTEXT_FEATURES, FEATURE_COLS, LEVEL_FEATURES,
                      QUALITY_FEATURES, SHAPE_FEATURES)
from size_effect import periods
from train_eval import feature_matrix_cols, make_logreg

N_BOOT = 1000   # same for every period, so the periods compare fairly
SEED = 42
# The team's feature groups, named as in the project slides
GROUPS = {**{f: "Size" for f in LEVEL_FEATURES}, **{f: "Movement" for f in SHAPE_FEATURES},
          **{f: "Stickiness" for f in QUALITY_FEATURES}, **{f: "Concentration" for f in CONCENTRATION_FEATURES},
          **{f: "Context" for f in CONTEXT_FEATURES}}


def coefficients(d: pd.DataFrame) -> pd.Series:
    """Standardised coefficient per numeric feature (category dummies dropped)."""
    cols = feature_matrix_cols(FEATURE_COLS)
    pipe = make_logreg(FEATURE_COLS).fit(d[cols], d[TARGET])
    names = [n.split("__", 1)[1] for n in pipe.named_steps["pre"].get_feature_names_out()]
    coef = pd.Series(pipe.named_steps["clf"].coef_[0], index=names)
    return coef[[n for n in names if n in GROUPS]]


def run(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    feature_rows, group_rows = [], []
    for period, mask in periods(df).items():
        name = period.split(" (")[0]
        d = df[mask].reset_index(drop=True)
        point = coefficients(d)
        boots = []
        for _ in range(N_BOOT):
            sample = d.iloc[rng.integers(0, len(d), len(d))]
            if sample[TARGET].nunique() == 2:
                boots.append(coefficients(sample))
        boots = pd.DataFrame(boots)
        for f, c in point.items():
            feature_rows.append({"period": name, "feature": f, "group": GROUPS[f], "coef": c,
                                 "coef_lo": boots[f].quantile(.025), "coef_hi": boots[f].quantile(.975),
                                 "share_positive": (boots[f] > 0).mean()})
        # A group's weight: its share of all absolute coefficients
        share = lambda c: c.abs().groupby(GROUPS).sum() / c.abs().sum()
        boot_share = boots.apply(share, axis=1)
        for g, w in share(point).items():
            group_rows.append({"period": name, "group": g, "weight": w,
                               "weight_lo": boot_share[g].quantile(.025), "weight_hi": boot_share[g].quantile(.975)})
    features = record(pd.DataFrame(feature_rows), "coef_by_period")

    # Rank of each size feature in each period (1 = largest absolute coefficient among features that vary)
    varying = features[features["coef"].abs() > 1e-9]
    ranks = varying.assign(rank=varying.groupby("period")["coef"].transform(lambda c: c.abs().rank(ascending=False)))
    size_ranks = ranks[ranks["group"] == "Size"].pivot_table(index="feature", columns="period", values="rank",
                                                              sort=False).astype(int)
    size_coef = ranks[ranks["group"] == "Size"].pivot_table(index="feature", columns="period", values="coef",
                                                             sort=False)
    record(size_ranks.join(size_coef, lsuffix=" rank", rsuffix=" coef").reset_index(), "size_ranks_by_period")

    # Largest coefficients in the last period, by size (either sign), with their share of all weight
    last = features[(features["period"] == features["period"].iloc[-1]) & (features["coef"].abs() > 1e-9)]
    last = last.assign(share=last["coef"].abs() / last["coef"].abs().sum()).sort_values("share", ascending=False)
    last["cumulative_share"] = last["share"].cumsum()
    last.insert(0, "rank", range(1, len(last) + 1))
    record(last[["rank", "feature", "group", "coef", "share", "cumulative_share", "share_positive"]],
           "coef_ranked_after_dencun")
    return record(pd.DataFrame(group_rows), "coef_groups_by_period")
