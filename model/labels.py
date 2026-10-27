"""Post-window sustained-success labels and survival durations.

All outcomes are measured AFTER the observation window (months >= k) so that
early activity levels cannot mechanically equal the label.
"""
from __future__ import annotations

import argparse
from typing import Optional

import numpy as np
import pandas as pd

from common import (
    annotate_lifecycle,
    load_lifecycle,
    load_panel,
    load_static,
    savetable,
    setup_style,
)

# Primary thresholds (tuned after inspecting base rates; see main()).
ABS_WALLETS_12 = 1_000
REL_OF_WINDOW_MAX = 0.25
DEATH_FRAC = 0.20
DEATH_STREAK = 3
ECO_SHARE_TOP_Q = 0.75  # top quartile of mean eco-share at months 10-12


def _window_slice(g: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    """Rows with months_since_launch in [lo, hi] inclusive."""
    msl = g["months_since_launch"].astype(float)
    return g[(msl >= lo) & (msl <= hi)].sort_values("months_since_launch")


def _mean_wallets(g: pd.DataFrame, lo: int, hi: int) -> float:
    s = _window_slice(g, lo, hi)
    if s.empty:
        return np.nan
    return float(s["active_wallets"].astype(float).mean())


def _mean_eco_share(g: pd.DataFrame, lo: int, hi: int) -> float:
    s = _window_slice(g, lo, hi)
    if s.empty or "share_of_ecosystem_active_wallets" not in s.columns:
        return np.nan
    return float(s["share_of_ecosystem_active_wallets"].astype(float).mean())


def _obs_window_max(g: pd.DataFrame, k: int) -> float:
    early = _window_slice(g, 0, k - 1)
    if early.empty:
        return np.nan
    return float(early["active_wallets"].astype(float).max())


def _obs_window_passed_1k(g: pd.DataFrame, k: int) -> bool:
    early = _window_slice(g, 0, k - 1)
    if early.empty:
        return False
    return bool(early["active_wallets"].astype(float).max() >= 1_000)


def survival_from_window(
    g: pd.DataFrame,
    k: int,
    death_frac: float = DEATH_FRAC,
    streak: int = DEATH_STREAK,
) -> tuple[float, int]:
    """Time (months) from end of window until death, plus event indicator.

    Death = wallets stay below death_frac * window_max for `streak` consecutive
    months after the observation window. Right-censored if never happens.
    Duration is measured from month k (first post-window month).
    """
    win_max = _obs_window_max(g, k)
    if not np.isfinite(win_max) or win_max <= 0:
        return np.nan, 0

    thresh = death_frac * win_max
    post = _window_slice(g, k, int(g["months_since_launch"].max()))
    if post.empty:
        return np.nan, 0

    below = (post["active_wallets"].astype(float).values < thresh).astype(int)
    msl = post["months_since_launch"].astype(int).values
    run = 0
    for i, b in enumerate(below):
        run = run + 1 if b else 0
        if run >= streak:
            # death month is the last of the streak; duration from k
            death_msl = int(msl[i])
            duration = max(1, death_msl - k + 1)
            return float(duration), 1

    # censored at last observed post-window month
    last_msl = int(msl[-1])
    duration = max(1, last_msl - k + 1)
    return float(duration), 0


def build_labels(
    panel: Optional[pd.DataFrame] = None,
    life: Optional[pd.DataFrame] = None,
    k: int = 3,
    abs_wallets: float = ABS_WALLETS_12,
    rel_of_max: float = REL_OF_WINDOW_MAX,
) -> pd.DataFrame:
    """Build per-slug labels for a given observation window length k."""
    if panel is None:
        panel = load_panel()
    if life is None:
        life = annotate_lifecycle(load_lifecycle(), load_static())

    life_idx = life.set_index("slug")
    rows = []
    for slug, g in panel.groupby("slug"):
        if slug not in life_idx.index:
            continue
        meta = life_idx.loc[slug]
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[0]
        g = g.sort_values("month")
        if "months_since_launch" not in g.columns:
            continue

        early = _window_slice(g, 0, k - 1)
        if len(early) < max(1, k // 2):
            continue

        win_max = _obs_window_max(g, k)
        passed_1k = _obs_window_passed_1k(g, k)

        mean_10_12 = _mean_wallets(g, 10, 12)
        mean_22_24 = _mean_wallets(g, 22, 24)
        eco_10_12 = _mean_eco_share(g, 10, 12)
        wallets_m12 = _mean_wallets(g, 12, 12)
        wallets_m24 = _mean_wallets(g, 24, 24)

        # Primary: absolute AND relative persistence
        y_sustained_12 = (
            int(mean_10_12 >= abs_wallets and mean_10_12 >= rel_of_max * win_max)
            if np.isfinite(mean_10_12) and np.isfinite(win_max)
            else np.nan
        )
        y_abs_12 = (
            int(mean_10_12 >= abs_wallets) if np.isfinite(mean_10_12) else np.nan
        )
        y_sustained_24 = (
            int(mean_22_24 >= abs_wallets and mean_22_24 >= rel_of_max * win_max)
            if np.isfinite(mean_22_24) and np.isfinite(win_max)
            else np.nan
        )

        # Conditional: only defined when early window already hit 1k
        y_cond_sustained_12 = y_sustained_12 if passed_1k else np.nan

        dur, event = survival_from_window(g, k)

        rows.append({
            "slug": slug,
            "k": k,
            "category_group": meta.get("category_group"),
            "parent_protocol": meta.get("parent_protocol"),
            "has_token": bool(meta.get("has_token")),
            "launch_year": int(meta["launch_month"].year)
            if pd.notna(meta.get("launch_month"))
            else np.nan,
            "launch_month": meta.get("launch_month"),
            "left_censored": bool(meta.get("left_censored", False)),
            "eligible_12m": bool(meta.get("eligible_12m", False)),
            "eligible_24m": bool(meta.get("eligible_24m", False)),
            "window_max_wallets": win_max,
            "passed_1k_in_window": int(passed_1k),
            "mean_wallets_10_12": mean_10_12,
            "mean_wallets_22_24": mean_22_24,
            "mean_eco_share_10_12": eco_10_12,
            "wallets_m12": wallets_m12,
            "wallets_m24": wallets_m24,
            "y_sustained_12": y_sustained_12,
            "y_abs_12": y_abs_12,
            "y_sustained_24": y_sustained_24,
            "y_cond_sustained_12": y_cond_sustained_12,
            "survival_duration": dur,
            "survival_event": event,
        })

    out = pd.DataFrame(rows)

    # Regime-neutral: top-quartile of eco-share among eligible non-censored
    mask = out["eligible_12m"] & ~out["left_censored"] & out["mean_eco_share_10_12"].notna()
    if mask.sum() >= 20:
        q = out.loc[mask, "mean_eco_share_10_12"].quantile(ECO_SHARE_TOP_Q)
        out["y_eco_topq_12"] = np.where(
            out["mean_eco_share_10_12"].notna(),
            (out["mean_eco_share_10_12"] >= q).astype(float),
            np.nan,
        )
        out["eco_share_q75"] = q
    else:
        out["y_eco_topq_12"] = np.nan
        out["eco_share_q75"] = np.nan

    return out


def base_rates(labels: pd.DataFrame, target: str = "y_sustained_12") -> pd.DataFrame:
    use = labels[labels["eligible_12m"] & ~labels["left_censored"]].copy()
    if target == "y_sustained_24":
        use = labels[labels["eligible_24m"] & ~labels["left_censored"]].copy()
    rows = []
    for year, g in use.groupby("launch_year"):
        y = g[target].dropna()
        rows.append({
            "launch_year": int(year) if pd.notna(year) else np.nan,
            "n": len(g),
            "n_labeled": int(y.notna().sum()) if hasattr(y, "notna") else len(y),
            "positive_rate": float(y.mean()) if len(y) else np.nan,
            "n_positive": int(y.sum()) if len(y) else 0,
            "target": target,
        })
    # overall
    y = use[target].dropna()
    rows.append({
        "launch_year": -1,
        "n": len(use),
        "n_labeled": len(y),
        "positive_rate": float(y.mean()) if len(y) else np.nan,
        "n_positive": int(y.sum()) if len(y) else 0,
        "target": target,
    })
    return pd.DataFrame(rows)


def recommend_threshold(labels: pd.DataFrame, min_rate: float = 0.08) -> dict:
    """Suggest abs threshold if current primary rate is too rare."""
    use = labels[labels["eligible_12m"] & ~labels["left_censored"]]
    rate = float(use["y_sustained_12"].dropna().mean()) if len(use) else 0.0
    suggestion = {
        "current_abs": ABS_WALLETS_12,
        "current_rel": REL_OF_WINDOW_MAX,
        "current_rate": rate,
        "ok": rate >= min_rate,
        "suggested_abs": ABS_WALLETS_12,
    }
    if rate < min_rate:
        for cand in (500, 250, 100):
            tmp = (
                (use["mean_wallets_10_12"] >= cand)
                & (use["mean_wallets_10_12"] >= REL_OF_WINDOW_MAX * use["window_max_wallets"])
            )
            r = float(tmp.mean()) if len(tmp) else 0.0
            if r >= min_rate:
                suggestion["suggested_abs"] = cand
                suggestion["suggested_rate"] = r
                break
    return suggestion


def main() -> None:
    setup_style()
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    args = parser.parse_args()

    print("== labels ==")
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())

    all_br = []
    for k in args.k:
        print(f"  building labels k={k}...")
        lab = build_labels(panel, life, k=k)
        savetable(lab, f"labels_k{k}.csv")
        for target in (
            "y_sustained_12",
            "y_abs_12",
            "y_sustained_24",
            "y_eco_topq_12",
            "y_cond_sustained_12",
        ):
            br = base_rates(lab, target)
            br["k"] = k
            all_br.append(br)
            overall = br[br["launch_year"] == -1]
            if len(overall):
                print(
                    f"    {target}: n={int(overall['n_labeled'].iloc[0])} "
                    f"rate={overall['positive_rate'].iloc[0]:.3f}"
                )
        rec = recommend_threshold(lab)
        print(f"    threshold check: {rec}")
        savetable(pd.DataFrame([rec]), f"threshold_check_k{k}.csv")

    if all_br:
        savetable(pd.concat(all_br, ignore_index=True), "base_rates.csv")
    print("== labels done ==")


if __name__ == "__main__":
    main()
