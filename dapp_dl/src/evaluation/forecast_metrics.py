"""Forecast metrics on the log1p(active_wallets) scale (clipped at 0), plus interval metrics."""
import numpy as np
import pandas as pd


def _pinball(y, q, tau):
    d = y - q
    return np.mean(np.maximum(tau * d, (tau - 1) * d))


def point_metrics(frame, models, naive="Naive"):
    y = frame.y.to_numpy()
    rows = []
    mae_naive = np.mean(np.abs(y - frame[naive].clip(lower=0)))
    for m in models:
        p = frame[m].clip(lower=0).to_numpy()
        mae = np.mean(np.abs(y - p))
        rows.append(
            {
                "model": m,
                "MAE_log": mae,
                "RMSE_log": np.sqrt(np.mean((y - p) ** 2)),
                "MAE_vs_naive": 1 - mae / mae_naive,
                "n": len(y),
            }
        )
    return pd.DataFrame(rows).set_index("model")


def by_group(frame, models, col, naive="Naive"):
    """MAE_log per model, split by the values of column `col` (e.g. horizon step, dApp age bucket)."""
    out = {key: point_metrics(f, models, naive).MAE_log for key, f in frame.groupby(col, observed=True)}
    return pd.DataFrame(out).T.rename_axis(col)


def interval_metrics(frame, prefix="DeepAR", level=80):
    y = frame.y.to_numpy()
    lo = frame[f"{prefix}-lo-{level}"].clip(lower=0).to_numpy()
    hi = frame[f"{prefix}-hi-{level}"].clip(lower=0).to_numpy()
    med = frame[f"{prefix}-median"].clip(lower=0).to_numpy()
    a = (100 - level) / 200
    return {
        "coverage": float(np.mean((y >= lo) & (y <= hi))),
        "nominal": level / 100,
        "mean_width_log": float(np.mean(hi - lo)),
        "pinball_lo": float(_pinball(y, lo, a)),
        "pinball_median": float(_pinball(y, med, 0.5)),
        "pinball_hi": float(_pinball(y, hi, 1 - a)),
    }
