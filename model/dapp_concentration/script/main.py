"""Q3 concentration: load and check the data once, then run every analysis.

    python script/main.py
"""
from __future__ import annotations

import pandas as pd

import monthly
import power_law
import yearly
from common import (DATA, METRICS, concentration, read_activity, read_categories, read_concentration, record,
                    setup_style, size_by_year)


def check_data(activity: pd.DataFrame, categories: pd.DataFrame, con: pd.DataFrame) -> None:
    """Data range and quality, and our concentration recomputed against concentration_month.csv."""
    quality = {
        "data_start": activity["month"].min().date(),
        "data_end": activity["month"].max().date(),
        "n_protocols": activity["protocol"].nunique(),
        "n_rows": len(activity),
        "duplicate_protocol_months": int(activity.duplicated(["protocol", "month"]).sum()),
        "rows_with_missing_values": int(activity[METRICS].isna().any(axis=1).sum()),
        "rows_with_negative_values": int((activity[METRICS] < 0).any(axis=1).sum()),
        "protocols_without_category": len(set(activity["protocol"]) - set(categories["protocol"])),
    }
    print(pd.Series(quality).to_string())

    act = activity.merge(categories, on="protocol", how="left")
    scopes = pd.concat([act.assign(scope="ecosystem"), act.assign(scope=act["category_group"])])
    ours = pd.DataFrame([{"scope": s, "month": m, "metric": metric, **concentration(g[metric])}
                         for metric in ("active_wallets", "tx_count", "gas_used")
                         for (s, m), g in scopes.groupby(["scope", "month"]) if (g[metric] > 0).any()])
    both = ours.merge(con, on=["scope", "month", "metric"], how="outer", suffixes=("_ours", "_file"))
    check = record(pd.DataFrame([{
        "rows_ours": int(both["hhi_ours"].notna().sum()),
        "rows_file": int(both["hhi_file"].notna().sum()),
        "n_dapps_mismatch": int((both["n_dapps_ours"] != both["n_dapps_file"]).sum()),
        "max_diff_top10": (both["top10_share_ours"] - both["top10_share_file"]).abs().max(),
        "max_diff_hhi": (both["hhi_ours"] - both["hhi_file"]).abs().max(),
        "max_diff_gini": (both["gini_ours"] - both["gini_file"]).abs().max(),
    }]), "check_vs_concentration_month")
    print(check.T.to_string(header=False))


def main() -> None:
    setup_style()
    activity = read_activity()
    categories = read_categories()
    con = read_concentration()
    sizes = size_by_year(activity, "active_wallets")
    sizes.rename(columns={"size": "avg_monthly_active_wallets"}).to_csv(DATA / "dapp_size_by_year.csv", index=False)

    print("== data check ==")
    check_data(activity, categories, con)
    print("\n== yearly sizes ==")
    yearly.run(activity, categories, sizes)
    print("\n== monthly concentration ==")
    monthly.run(activity, categories, con)
    print("\n== power-law test ==")
    power_law.run(sizes)


if __name__ == "__main__":
    main()
