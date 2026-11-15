"""Test: is the DApp size distribution a power law? Clauset, Shalizi & Newman (2009), one fit per year.

1. Estimate alpha by maximum likelihood and pick x_min with the smallest KS distance, keeping at least 50 DApps in the tail
2. Goodness of fit for each model on the same tail: parametric bootstrap p-value (p <= 0.1 rejects it)
3. Power law vs log-normal: Vuong likelihood-ratio test (R > 0 favours power law)

Follows the R package poweRlaw (conpl, conlnorm, bootstrap_p, compare_distributions) step by step.
Bootstrap p-values are random, so another seed moves them slightly; the verdicts do not change.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

from common import record, savefig

N_SIMS = 1000    # bootstrap data sets per year and model
P_ALPHA = 0.1    # bootstrap p at or below this rejects the model
MIN_TAIL = 50    # without it the KS search can pick a tail of only ~20 DApps
SEED = 1


# ---- power law (continuous) ----

def pl_scan(x: np.ndarray, xmins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """alpha and KS distance for every candidate x_min at once; x must be sorted ascending."""
    start = np.searchsorted(x, xmins, side="left")
    n_tail = len(x) - start
    log_x = np.log(x)
    sum_log_tail = np.concatenate([np.cumsum(log_x[::-1])[::-1], [0.0]])[start]
    alpha = 1 + n_tail / (sum_log_tail - n_tail * np.log(xmins))

    j = np.arange(len(x))[None, :]
    in_tail = j >= start[:, None]
    data_cdf = (j - start[:, None]) / n_tail[:, None]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        fit_cdf = 1 - (x[None, :] / xmins[:, None]) ** (1 - alpha[:, None])
    ks = np.where(in_tail, np.abs(fit_cdf - data_cdf), 0).max(axis=1)
    return alpha, ks


def pl_fit(x: np.ndarray, xmins: np.ndarray) -> dict:
    alpha, ks = pl_scan(np.sort(x), xmins)
    i = int(np.argmin(ks))
    return {"xmin": xmins[i], "alpha": alpha[i], "ks": ks[i]}


def pl_logpdf(q: np.ndarray, xmin: float, alpha: float) -> np.ndarray:
    return np.log((alpha - 1) / xmin) - alpha * np.log(q / xmin)


def pl_sf(q: np.ndarray, xmin: float, alpha: float) -> np.ndarray:
    return (q / xmin) ** (1 - alpha)


def pl_rand(rng: np.random.Generator, n: int, xmin: float, alpha: float) -> np.ndarray:
    return xmin * (1 - rng.random(n)) ** (-1 / (alpha - 1))


# ---- log-normal truncated at x_min ----

def ln_logpdf(q: np.ndarray, xmin: float, mu: float, sigma: float) -> np.ndarray:
    return stats.lognorm.logpdf(q, sigma, scale=np.exp(mu)) - stats.lognorm.logsf(xmin, sigma, scale=np.exp(mu))


def ln_sf(q: np.ndarray, xmin: float, mu: float, sigma: float) -> np.ndarray:
    return np.exp(stats.lognorm.logsf(q, sigma, scale=np.exp(mu)) - stats.lognorm.logsf(xmin, sigma, scale=np.exp(mu)))


def ln_mle(x: np.ndarray, xmin: float) -> tuple[float, float]:
    """Same as poweRlaw's conlnorm$mle: fit on x > xmin, L-BFGS-B from the log mean and sd."""
    tail = x[x > xmin]
    log_tail = np.log(tail)

    def negloglike(par):
        r = -ln_logpdf(tail, xmin, par[0], par[1]).sum()
        return r if np.isfinite(r) else 1e12

    res = optimize.minimize(negloglike, [log_tail.mean(), log_tail.std(ddof=1)], method="L-BFGS-B",
                            bounds=[(None, None), (np.finfo(float).eps, None)])
    return float(res.x[0]), float(res.x[1])


def ln_ks(x: np.ndarray, xmin: float, mu: float, sigma: float) -> float:
    tail = np.sort(x[x >= xmin])
    n = len(tail)
    return float(np.max(np.abs((1 - ln_sf(tail, xmin, mu, sigma)) - np.arange(n) / n)))


def ln_rand(rng: np.random.Generator, n: int, xmin: float, mu: float, sigma: float) -> np.ndarray:
    """Draws from the log-normal above xmin (inverse CDF; same distribution as poweRlaw's rejection sampler)."""
    lo = stats.norm.cdf((np.log(xmin) - mu) / sigma)
    u = lo + (1 - lo) * rng.random(n)
    return np.exp(mu + sigma * stats.norm.ppf(u))


# ---- bootstrap and Vuong ----

def bootstrap_sample(rng, x: np.ndarray, xmin: float, draw_tail) -> np.ndarray:
    """poweRlaw's sample_p_helper: below x_min resample the data, above it draw from the fitted model."""
    n = len(x)
    n_lower = int((rng.random(n) > np.mean(x >= xmin)).sum())
    return np.concatenate([rng.choice(x[x < xmin], n_lower, replace=True), draw_tail(n - n_lower)])


def fit_year(x: np.ndarray, rng: np.random.Generator) -> dict:
    # Candidate x_min values that leave at least MIN_TAIL DApps
    xmins = np.unique(x)
    xmins = xmins[np.array([(x >= m).sum() for m in xmins]) >= MIN_TAIL]

    pl = pl_fit(x, xmins)
    xmin = pl["xmin"]
    mu, sigma = ln_mle(x, xmin)   # log-normal on the same tail so the two fits are comparable
    tail = x[x >= xmin]

    pl_ks_sims = [pl_fit(bootstrap_sample(rng, x, xmin, lambda k: pl_rand(rng, k, xmin, pl["alpha"])), xmins)["ks"]
                  for _ in range(N_SIMS)]
    ln_obs = ln_ks(x, xmin, mu, sigma)
    ln_ks_sims = []
    for _ in range(N_SIMS):
        q = bootstrap_sample(rng, x, xmin, lambda k: ln_rand(rng, k, xmin, mu, sigma))
        ln_ks_sims.append(ln_ks(q, xmin, *ln_mle(q, xmin)))

    ratio = pl_logpdf(tail, xmin, pl["alpha"]) - ln_logpdf(tail, xmin, mu, sigma)
    vuong_r = np.sqrt(len(ratio)) * ratio.mean() / ratio.std(ddof=1)
    p1 = stats.norm.cdf(vuong_r)

    return {"summary": {"n_dapps": len(x), "n_tail": len(tail), "x_min": xmin, "alpha": pl["alpha"], "ks": pl["ks"],
                        "p_power_law": np.mean(np.array(pl_ks_sims) >= pl["ks"]),
                        "p_lognormal": np.mean(np.array(ln_ks_sims) >= ln_obs),
                        "vuong_r": vuong_r, "vuong_p": 2 * min(p1, 1 - p1)},
            "x": x, "xmin": xmin, "alpha": pl["alpha"], "mu": mu, "sigma": sigma}


def verdict(r: pd.Series) -> str:
    pl_ok, ln_ok = r["p_power_law"] > P_ALPHA, r["p_lognormal"] > P_ALPHA
    if not pl_ok and not ln_ok:
        return "neither fits"
    if pl_ok and not ln_ok:
        return "power law only"
    if ln_ok and not pl_ok:
        return "log-normal only"
    if r["vuong_p"] < P_ALPHA:
        return "both plausible, power law better" if r["vuong_r"] > 0 else "both plausible, log-normal better"
    return "both plausible, cannot tell apart"


def run(sizes: pd.DataFrame) -> None:
    rng = np.random.default_rng(SEED)

    # Fit each year
    fits = {year: fit_year(g["size"].to_numpy(float), rng)
            for year, g in sizes.groupby("year")}
    power_law = pd.DataFrame([{"year": y, **f["summary"]} for y, f in fits.items()])
    power_law["verdict"] = power_law.apply(verdict, axis=1)
    cols = ["alpha", "ks", "p_power_law", "p_lognormal", "vuong_r", "vuong_p"]
    power_law[cols] = power_law[cols].round(3)
    power_law["x_min"] = power_law["x_min"].round().astype(int)
    record(power_law, "power_law_by_year")
    print(power_law.to_string(index=False))

    # Tail plot (share of DApps at least this size, log-log)
    fig, axes = plt.subplots(2, 3, sharex=True, sharey=True)
    for ax, (year, f) in zip(axes.flat, fits.items()):
        x = np.sort(f["x"])
        n = len(x)
        ax.scatter(x, (n - np.arange(n)) / n, s=4, color="#7F7F7F", lw=0)
        grid = np.geomspace(f["xmin"], x.max(), 200)
        scale = np.mean(x >= f["xmin"])
        ax.plot(grid, scale * pl_sf(grid, f["xmin"], f["alpha"]), color="#eb6834", lw=1.2, label="power law")
        ax.plot(grid, scale * ln_sf(grid, f["xmin"], f["mu"], f["sigma"]), color="#2a78d6", lw=1.2,
                label="log-normal")
        ax.set(xscale="log", yscale="log", title=str(year))
        ax.set_xticks([1, 1e2, 1e4, 1e6], ["1", "100", "10K", "1M"])
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.minorticks_off()
    for ax in axes[1]:
        ax.set_xlabel("Average monthly active wallets")
    for ax in axes[:, 0]:
        ax.set_ylabel("P(size >= x)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=2)
    savefig(fig, "power_law_tail")

