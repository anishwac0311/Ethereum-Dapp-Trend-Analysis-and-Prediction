"""Time-split checks for the team model: fix the training-answer leakage, test across two market events, compare
how strongly early size predicts success in each period, and which features drive success in each period.

    python script/main.py
"""
from __future__ import annotations

import pandas as pd

from config import DATA, K, TARGET, record  # first: puts the team model on the import path
import plots
import coef_by_period
import size_effect
from evaluate import evaluate
from features import build_dataset
from splits import assignment, define_splits
from train_eval import eligible_frame


def main() -> None:
    df = eligible_frame(build_dataset(K), TARGET)
    df["launch_month"] = pd.to_datetime(df["launch_month"])
    splits = define_splits(df)
    assignment(df, splits).to_csv(DATA / "split_assignment.csv", index=False)

    sizes, scores = [], []
    for name, (train_mask, test_mask) in splits.items():
        train, test = df[train_mask], df[test_mask]
        sizes.append({"split": name,
                      "train_launches": f"{train['launch_month'].min():%Y-%m} to {train['launch_month'].max():%Y-%m}",
                      "test_launches": f"{test['launch_month'].min():%Y-%m} to {test['launch_month'].max():%Y-%m}",
                      "n_train": len(train), "pos_train": int(train[TARGET].sum()),
                      "n_test": len(test), "pos_test": int(test[TARGET].sum()),
                      "n_unused": int((~train_mask & ~test_mask).sum())})
        print(f"== {name}: train {len(train)} ({int(train[TARGET].sum())} successful), "
              f"test {len(test)} ({int(test[TARGET].sum())} successful)")
        scores.append(evaluate(train, test, name))
    record(pd.DataFrame(sizes), "split_sizes")
    scores = record(pd.concat(scores, ignore_index=True), "holdout_scores")

    ap = scores.pivot_table(index="model", columns="split", values="ap", sort=False)
    auc = scores.pivot_table(index="model", columns="split", values="auc", sort=False)
    leakage = pd.DataFrame({"ap_current": ap["current"], "ap_leakage_fixed": ap["leakage_fixed"],
                            "ap_change": ap["leakage_fixed"] - ap["current"],
                            "auc_current": auc["current"], "auc_leakage_fixed": auc["leakage_fixed"],
                            "auc_change": auc["leakage_fixed"] - auc["current"]}).reset_index()
    record(leakage, "leakage_check")
    rounds = scores[scores["split"].isin(["round_1", "round_2"])]
    record(rounds, "event_rounds")

    # How much the learned models add over size alone (Szabo-Huberman), on each split
    size_only = scores[scores["model"] == "szabo_huberman"].set_index("split")["ap"]
    vs = scores[scores["model"].isin(["logreg_l2", "logreg_elastic", "hgb", "hgb_calibrated"])][["split", "model", "ap"]]
    vs = vs.assign(ap_size_only=vs["split"].map(size_only), ap_minus_size_only=lambda d: d["ap"] - d["ap_size_only"])
    record(vs, "vs_szabo_huberman")

    print("\nAP by split:")
    print(ap.round(3).to_string())

    print("\nSize effect by period:")
    print(size_effect.run(df).round(3).to_string(index=False))

    print("\nCoefficient weight by feature group and period:")
    groups = coef_by_period.run(df)
    print(groups.pivot_table(index="group", columns="period", values="weight", sort=False).round(3).to_string())
    plots.run()


if __name__ == "__main__":
    main()
