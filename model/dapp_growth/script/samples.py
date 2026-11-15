"""Build the growth tables on two clocks: from the deploy month (512 DApps) and from the first user (486 DApps)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import (DATA, LAST_MONTH, PANEL_START, WINDOWS, growth_table, milestones_table, record, success_table,
                    wallets_table)


def summarise(sample: pd.DataFrame, monthly: pd.DataFrame, months: pd.DataFrame, clock: str) -> pd.DataFrame:
    tables = [success_table(monthly, clock), milestones_table(months, clock), wallets_table(monthly, clock),
              growth_table(monthly, clock)]
    out = sample
    for t in tables:
        out = out.merge(t, on="slug", how="left")
    return out


def checks(monthly: pd.DataFrame, summary: pd.DataFrame, n_dapps: int) -> dict:
    """Checks shared by both tables."""
    success = summary[[f"success_k{k}" for k in WINDOWS]].to_numpy()
    return {
        "monthly rows = dapps x 13": len(monthly) == n_dapps * 13,
        "one summary row per DApp": summary["slug"].is_unique and len(summary) == n_dapps,
        "no success is NA": not np.isnan(success).any(),
        "success never goes 0 to 1 as k grows": bool((np.diff(success, axis=1) <= 0).all()),
        "success_k implies success_abs": bool((success <= summary[["success_abs"]].to_numpy()).all()),
        "5k never before 1k": not (summary["months_to_1k"] > summary["months_to_5k"]).any(),
        "10k never before 5k": not (summary["months_to_5k"] > summary["months_to_10k"]).any(),
    }


def deploy_clock(panel: pd.DataFrame) -> tuple[pd.DataFrame, list, dict]:
    """Month 0 = deploy month. Same 512 DApps as model/labels.py."""
    dapps = panel.groupby("slug").agg(category_group=("category_group", "first"),
                                      parent_protocol=("parent_protocol", "first"),
                                      first_deployed=("first_deployed", "first"), launch_month=("month", "min"),
                                      observed_months=("months_since_launch", "max")).reset_index()
    dapps["observed_months"] += 1
    dapps["launch_date_known"] = dapps["first_deployed"].notna()
    # DApps with no deploy date start at 2020-01 in the panel; launch_date_known flags them
    in_panel = dapps[~dapps["launch_date_known"] | (dapps["first_deployed"] >= PANEL_START)]
    sample = in_panel[in_panel["observed_months"] > LAST_MONTH]

    rows = panel[panel["slug"].isin(sample["slug"])]
    monthly = rows[rows["months_since_launch"] <= LAST_MONTH]
    summary = summarise(sample, monthly, rows, "months_since_launch")
    summary.to_csv(DATA / "dapp_growth_summary.csv", index=False)

    steps = [("deploy", "all DApps in panel", len(dapps)),
             ("deploy", "launched from 2020 or date unknown", len(in_panel)),
             ("deploy", "observed through month 12", len(sample))]
    return summary, steps, checks(monthly, summary, len(sample))


def first_user_clock(panel: pd.DataFrame) -> tuple[pd.DataFrame, list, dict]:
    """Month 0 = first month with any wallet, so a missing or early deploy date no longer matters."""
    has_user = panel[panel["cum_wallets"] >= 1].groupby("slug").first()
    dapps = panel.groupby("slug").agg(category_group=("category_group", "first"),
                                      parent_protocol=("parent_protocol", "first"),
                                      first_deployed=("first_deployed", "first"),
                                      last_months_since_launch=("months_since_launch", "max"))
    dapps["first_user_month"] = has_user["month"]
    dapps["months_deploy_to_first_user"] = has_user["months_since_launch"]
    dapps["launch_date_known"] = dapps["first_deployed"].notna()
    dapps["observed_months"] = dapps["last_months_since_launch"] - dapps["months_deploy_to_first_user"] + 1
    dapps = dapps.reset_index()

    in_panel = dapps[~dapps["launch_date_known"] | (dapps["first_deployed"] >= PANEL_START)]
    with_users = in_panel[in_panel["first_user_month"].notna()]
    sample = with_users[with_users["observed_months"] > LAST_MONTH].drop(columns="last_months_since_launch")
    sample = sample.astype({"months_deploy_to_first_user": int, "observed_months": int})

    rows = panel.merge(sample[["slug", "months_deploy_to_first_user"]], on="slug")
    rows["months_since_first_user"] = rows["months_since_launch"] - rows["months_deploy_to_first_user"]
    rows = rows[rows["months_since_first_user"] >= 0]
    monthly = rows[rows["months_since_first_user"] <= LAST_MONTH]
    summary = summarise(sample, monthly, rows, "months_since_first_user")
    summary.to_csv(DATA / "dapp_growth_first_user_summary.csv", index=False)

    steps = [("first user", "all DApps in panel", len(dapps)),
             ("first user", "launched from 2020 or date unknown", len(in_panel)),
             ("first user", "has at least one user", len(with_users)),
             ("first user", "observed 13 months from the first user", len(sample))]
    result = checks(monthly, summary, len(sample))
    result["month 0 is the first month with a wallet"] = bool(
        (monthly.loc[monthly["months_since_first_user"] == 0, "cum_wallets"] >= 1).all())
    return summary, steps, result


def run(panel: pd.DataFrame) -> None:
    _, deploy_steps, deploy_checks = deploy_clock(panel)
    _, user_steps, user_checks = first_user_clock(panel)
    record(pd.DataFrame(deploy_steps + user_steps, columns=["clock", "step", "n_dapps"]), "sample_steps")
    for name, ok in {**deploy_checks, **user_checks}.items():
        assert ok, f"check failed: {name}"
    print(pd.DataFrame(deploy_steps + user_steps, columns=["clock", "step", "n_dapps"]).to_string(index=False))
    print(f"all {len(deploy_checks) + len(user_checks)} table checks passed")
