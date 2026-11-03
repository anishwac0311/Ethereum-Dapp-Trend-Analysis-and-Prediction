"""From activity.csv: monthly totals, yearly DApp sizes, yearly concentration, Lorenz curves and the top 10.

Size of a DApp in a year = its average monthly active wallets (months without activity count as 0).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import PercentFormatter

from common import METRICS, TOP_K, YEAR_COLOURS, concentration, record, savefig, size_by_year

CATEGORY_COLOURS = {"DEX": "#2a78d6", "DeFi": "#eb6834", "Infrastructure": "#1baf7a",
                    "NFT": "#9B59B6", "Gaming": "#eda100", "Other": "#898781"}


def log_density(x: np.ndarray, n_grid: int = 512) -> tuple[np.ndarray, np.ndarray]:
    """Gaussian KDE of log10(x) with R's default bandwidth (bw.nrd0) over the data range, as geom_density on a log10 axis."""
    z = np.log10(x)
    iqr = np.subtract(*np.percentile(z, [75, 25]))
    bw = 0.9 * min(z.std(ddof=1), iqr / 1.34) * len(z) ** -0.2
    grid = np.linspace(z.min(), z.max(), n_grid)
    dens = np.exp(-0.5 * ((grid[:, None] - z[None, :]) / bw) ** 2).sum(axis=1) / (len(z) * bw * np.sqrt(2 * np.pi))
    return grid, dens


def activity_by_month(activity: pd.DataFrame) -> None:
    """Monthly totals over all DApps (wallets summed over DApps, so a wallet using two DApps counts twice)."""
    monthly = activity.groupby("month").agg(
        active_dapps=("active_wallets", lambda s: (s > 0).sum()), active_wallets=("active_wallets", "sum"),
        tx_count=("tx_count", "sum"), gas_used=("gas_used", "sum"))
    by_year = monthly.groupby(monthly.index.year).mean()
    by_year["tx_per_wallet"] = by_year["tx_count"] / by_year["active_wallets"]
    record(by_year.round(2).rename_axis("year").reset_index(), "activity_by_year")

    panels = [("active_dapps", "Active DApps", 1), ("active_wallets", "Active wallets (M)", 1e6),
              ("tx_count", "Transactions (M)", 1e6), ("gas_used", "Gas used (trillions)", 1e12)]
    fig, axes = plt.subplots(2, 2, sharex=True)
    for ax, (col, title, unit) in zip(axes.flat, panels):
        ax.plot(monthly.index, monthly[col] / unit, color="#1D3B56", lw=1)
        ax.set_title(title, fontsize=10)
    savefig(fig, "activity_by_month")


def size_distribution(sizes: pd.DataFrame, categories: pd.DataFrame) -> None:
    """Size quantiles, the five largest DApps per year, and the density of log size."""
    q = sizes.groupby("year")["size"]
    quantiles = pd.DataFrame({
        "n_dapps": q.size(), "n_under_10_wallets": q.apply(lambda s: int((s < 10).sum())),
        "p25": q.quantile(.25), "median": q.median(), "p75": q.quantile(.75),
        "p99": q.quantile(.99), "max": q.max(),
    }).round().reset_index()
    record(quantiles, "size_quantiles_by_year")

    largest = sizes.assign(share=sizes["size"] / q.transform("sum"),
                           rank=q.rank(method="min", ascending=False).astype(int))
    largest = (largest[largest["rank"] <= 5].sort_values(["year", "rank"])
               .merge(categories, on="protocol", how="left")
               .rename(columns={"size": "avg_monthly_active_wallets"})
               [["year", "rank", "protocol", "category_group", "avg_monthly_active_wallets", "share"]])
    largest["avg_monthly_active_wallets"] = largest["avg_monthly_active_wallets"].round().astype(int)
    largest["share"] = largest["share"].round(3)
    record(largest, "largest_dapps_by_year")

    fig, ax = plt.subplots()
    for year, g in sizes.groupby("year"):
        grid, dens = log_density(g["size"].to_numpy())
        ax.plot(10 ** grid, dens, color=YEAR_COLOURS[year], lw=1, label=str(year))
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
    ax.set(xlabel="Average monthly active wallets (log)", ylabel="Density")
    ax.legend(title="Year", loc="center left", bbox_to_anchor=(1, 0.5))
    savefig(fig, "size_density_by_year")


def concentration_by_year(activity: pd.DataFrame, categories: pd.DataFrame, sizes: pd.DataFrame) -> None:
    """Top-k share, HHI and Gini per year for four metrics and two units, plus Lorenz curves.

    Units: single protocols, and protocols merged by parent_protocol (uniswap-v2, v3 and v4 counted as one uniswap).
    """
    merged = activity.merge(categories, on="protocol", how="left")
    merged["parent_protocol"] = merged["parent_protocol"].fillna(merged["protocol"])
    activity_parent = merged.groupby(["parent_protocol", "month"], as_index=False)[METRICS].sum()

    rows = []
    for metric in sorted(METRICS):
        for unit in ("parent_protocol", "protocol"):
            data = activity if unit == "protocol" else activity_parent
            for year, g in size_by_year(data, metric, unit).groupby("year"):
                rows.append({"metric": metric, "unit": unit, "year": year, **concentration(g["size"])})
    record(pd.DataFrame(rows), "concentration_by_year")

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], ls="--", color="#999999", lw=0.8)
    for year, g in sizes.groupby("year"):
        s = np.sort(g["size"].to_numpy())
        ax.plot(np.arange(1, len(s) + 1) / len(s), np.cumsum(s) / s.sum(), color=YEAR_COLOURS[year], lw=1,
                label=str(year))
    ax.set(xlabel="Share of DApps (smallest first)", ylabel="Share of active wallets", aspect="equal")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(title="Year", loc="center left", bbox_to_anchor=(1, 0.5))
    savefig(fig, "lorenz_by_year")


def leaders(sizes: pd.DataFrame, categories: pd.DataFrame) -> None:
    """Do the same DApps stay in the top 10? Turnover, categories of the top 10, and membership by year."""
    sizes = sizes.assign(share=sizes["size"] / sizes.groupby("year")["size"].transform("sum"),
                         rank=sizes.groupby("year")["size"].rank(method="min", ascending=False).astype(int))
    top10 = sizes[sizes["rank"] <= TOP_K].sort_values(["year", "rank"])
    years = sorted(top10["year"].unique())

    rows = []
    for y in years[1:]:
        this_year = top10[top10["year"] == y]
        stayed = this_year["protocol"].isin(top10.loc[top10["year"] == y - 1, "protocol"])
        rows.append({"year": y, "n_stayed_from_last_year": int(stayed.sum()),
                     "share_held_by_stayers": round(this_year.loc[stayed, "share"].sum(), 3),
                     "share_held_by_new_entrants": round(this_year.loc[~stayed, "share"].sum(), 3)})
    record(pd.DataFrame(rows), "top10_turnover")

    counts = (top10.merge(categories, on="protocol", how="left")
              .pivot_table(index="category_group", columns="year", values="protocol", aggfunc="count", fill_value=0)
              .sort_index()
              .sort_values(years[-1], ascending=False, kind="stable"))
    table = counts.copy()
    table.columns = table.columns.astype(str)
    record(table.reset_index(), "top10_by_category")

    fig, ax = plt.subplots()
    for category, n in counts.iterrows():
        ax.plot(n.index, n.values, marker="o", ms=5, lw=1.6, color=CATEGORY_COLOURS[category], label=category)
    ax.set(xticks=years, yticks=range(7), ylabel="DApps in the top 10")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=len(counts))
    savefig(fig, "top10_by_category")

    # Membership: most years in the top 10 at the bottom, ties alphabetical
    n_years = top10.groupby("protocol")["year"].size()
    order = sorted(n_years.index, key=lambda p: (-n_years[p], p))
    grid = top10.pivot(index="protocol", columns="year", values="rank").reindex(order)

    cmap = LinearSegmentedColormap.from_list("rank", ["#1f4e7a", "#c9dbea"])
    fig, ax = plt.subplots()
    mesh = ax.pcolormesh(np.ma.masked_invalid(grid.to_numpy(float)), cmap=cmap, vmin=1, vmax=TOP_K,
                         edgecolors="white", linewidth=0.8)
    for i, j in zip(*np.where(grid.notna().to_numpy())):
        rank = int(grid.iat[i, j])
        ax.text(j + .5, i + .5, rank, ha="center", va="center", fontsize=7,
                color="white" if rank <= 5 else "#262626")
    ax.set_xticks(np.arange(len(years)) + .5, years)
    ax.set_yticks(np.arange(len(order)) + .5, order)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(False)
    cbar = fig.colorbar(mesh, ax=ax, shrink=.25, aspect=8)
    cbar.set_ticks([1, 4, 7, 10])
    cbar.ax.invert_yaxis()
    cbar.outline.set_visible(False)
    cbar.set_label("Rank")
    savefig(fig, "top10_membership")


def run(activity: pd.DataFrame, categories: pd.DataFrame, sizes: pd.DataFrame) -> None:
    activity_by_month(activity)
    size_distribution(sizes, categories)
    concentration_by_year(activity, categories, sizes)
    leaders(sizes, categories)
