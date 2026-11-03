"""Test the candidate features in the team model: same split and models as model/train_eval.py, k = 3.

Needs the team's model code with on-chain and off-chain feature groups (ONCHAIN_FEATURES, OFFCHAIN_FEATURES in
model/features.py, first added on the offchain-feature-modelling branch). Not run by main.py:

    python script/test_features.py [path/to/model]
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA, ROOT, record, savefig, setup_style

K = 3
ACQUISITION = ["log_cum_wallets_k", "cum_growth_last", "growth_decay", "months_to_first_user_k", "starts_empty"]
CONTEXT = ["category_hhi_at_launch", "category_top1_share_at_launch", "category_n_dapps_at_launch"]
MODELS = {"logreg_l2": "Logistic (L2)", "logreg_elastic": "Logistic (elastic-net)", "hgb": "Boosted trees",
          "hgb_calibrated": "Boosted trees, calibrated"}
SHOWN = "hgb_calibrated"   # the team's headline model


def plot(results: pd.DataFrame) -> None:
    """One bar per variant for the headline model, with the 95% bootstrap interval."""
    setup_style()
    shown = results[results["model"] == SHOWN].reset_index(drop=True)
    base = shown["ap"].iloc[0]
    fig, ax = plt.subplots()
    y = np.arange(len(shown))
    colours = ["#55301F" if i == 0 else ("#C68B6A" if "off-chain" not in v else "#A3A6AD")
               for i, v in enumerate(shown["variant"])]
    ax.set_axisbelow(True)
    ax.barh(y, shown["ap"], color=colours, height=.6)
    ax.errorbar(shown["ap"], y, xerr=[shown["ap"] - shown["ap_lo"], shown["ap_hi"] - shown["ap"]], fmt="none",
                ecolor="#6B7280", elinewidth=1, capsize=3)
    for i, ap in enumerate(shown["ap"]):
        ax.text(.02, i, f"{ap:.2f}", va="center", color="white", fontsize=9, fontweight="bold")
    ax.axvline(base, ls="--", color="#55301F", lw=1)
    ax.set_yticks(y, shown["variant"])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set(xlim=(0, 1), xlabel=f"Holdout score (average precision), {K} months seen")
    ax.set_title(f"{MODELS[SHOWN]}; whiskers: 95% bootstrap interval; dashed: team best", fontsize=9, color="#4D4D4D")
    savefig(fig, f"feature_test_k{K}")


def main() -> None:
    model_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "model"
    # The team model has its own common.py; load it in place of ours (our helpers are already imported)
    sys.modules.pop("common", None)
    sys.path.insert(0, str(model_dir))
    import train_eval as te
    from features import OFFCHAIN_FEATURES, ONCHAIN_FEATURES, build_dataset

    ds = build_dataset(K)
    new = pd.read_csv(DATA / "dapp_acquisition_features.csv")
    ds = ds.merge(new[new["k"] == K], on=["slug", "k"], how="left")

    on, off = list(ONCHAIN_FEATURES), list(OFFCHAIN_FEATURES)
    variants = {
        "On-chain only (team best)": on,
        "+ Acquisition (5)": on + ACQUISITION,
        "+ Context from Q3 (3)": on + CONTEXT,
        "+ Acquisition + Context (8)": on + ACQUISITION + CONTEXT,
        "+ starts_empty, growth_decay": on + ["starts_empty", "growth_decay"],
        "On-chain + off-chain (team full)": on + off,
        "On-chain + off-chain + all 8": on + off + ACQUISITION + CONTEXT,
    }
    rows = []
    for name, cols in variants.items():
        res = te.run_for_k(ds, K, feature_cols=cols, tag_suffix="_candidates")["results"]
        res = res[res["model"].isin(MODELS)].assign(variant=name)
        rows.append(res[["variant", "model", "auc", "ap", "ap_lo", "ap_hi", "precision_at_10pct"]])
    results = record(pd.concat(rows), f"feature_test_k{K}")

    plot(results)

    print(results.pivot_table(index="variant", columns="model", values="ap", sort=False).round(3).to_string())


if __name__ == "__main__":
    main()
