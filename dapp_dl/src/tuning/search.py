"""Optuna searches.

    python -m src.tuning.search nhits  [n_trials]
    python -m src.tuning.search deepar [n_trials]

N-HiTS and DeepAR are tuned on rolling windows that END BEFORE the test period: the data is
cut at TUNE_END (2024-12), so the 2025 test windows used in run_forecast never influence the
search. N-HiTS minimises MAE on log wallets; DeepAR minimises the sum of the 10/50/90%
pinball losses, which rewards calibrated intervals as well as accurate medians.

DeepSurv is tuned inside run_survival (`--tune`), separately for every outer split, using
only that split's train/validation parts (see `tune_deepsurv`).
"""
import copy
import sys
import warnings

import numpy as np
import optuna
import pandas as pd
import yaml

from src.data.build_forecast_panel import build_forecast_panel
from src.evaluation.forecast_metrics import interval_metrics, point_metrics
from src.models.deepar import run_deepar
from src.models.nhits import run_nhits

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

TUNE_END = "2024-12-01"


def tuning_data(cfg):
    fc = cfg["forecast"]
    df, static = build_forecast_panel(cfg["raw_dir"], fc["min_peak_wallets"], fc["min_series_len"])
    df = df[df.ds <= TUNE_END]
    keep = df.groupby("unique_id").size()
    keep = keep[keep >= fc["min_series_len"]].index
    return df[df.unique_id.isin(keep)].reset_index(drop=True), static[static.unique_id.isin(keep)].reset_index(drop=True)


def _save(study, base, to_cfg, name):
    cfg = to_cfg(base, study.best_params)
    yaml.safe_dump(cfg, open(f"configs/{name}_tuned.yaml", "w"), sort_keys=False)
    trials = study.trials_dataframe()
    trials.to_csv(f"results/tuning_{name}.csv", index=False)
    print(f"best {name}: value={study.best_value:.4f} params={study.best_params}")


def tune_nhits(n_trials=12):
    cfg = yaml.safe_load(open("configs/data.yaml"))
    base = yaml.safe_load(open("configs/nhits.yaml"))
    df, static = tuning_data(cfg)
    h, nw = cfg["forecast"]["horizon"], cfg["forecast"]["n_windows"]

    def to_cfg(b, p):
        c = copy.deepcopy(b)
        c.update(
            input_size=p["input_size"], learning_rate=p["learning_rate"],
            dropout_prob_theta=p["dropout"], max_steps=p["max_steps"],
            mlp_units=[[p["width"], p["width"]]] * 3,
        )
        return c

    def objective(trial):
        p = {
            "input_size": trial.suggest_categorical("input_size", [6, 9, 12]),
            "learning_rate": trial.suggest_float("learning_rate", 3e-4, 3e-3, log=True),
            "dropout": trial.suggest_float("dropout", 0.0, 0.3),
            "max_steps": trial.suggest_categorical("max_steps", [300, 600, 900]),
            "width": trial.suggest_categorical("width", [128, 256, 512]),
        }
        cv = run_nhits(df, static, to_cfg(base, p), h, nw, seed=1)
        return float(np.mean(np.abs(cv.y - cv.NHITS.clip(lower=0))))

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=0))
    study.enqueue_trial({"input_size": 12, "learning_rate": 1e-3, "dropout": 0.1, "max_steps": 300, "width": 256})  # current default
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    _save(study, base, to_cfg, "nhits")


def tune_deepar(n_trials=10):
    cfg = yaml.safe_load(open("configs/data.yaml"))
    base = yaml.safe_load(open("configs/deepar.yaml"))
    df, static = tuning_data(cfg)
    h, nw = cfg["forecast"]["horizon"], cfg["forecast"]["n_windows"]

    def to_cfg(b, p):
        c = copy.deepcopy(b)
        c.update(
            input_size=p["input_size"], learning_rate=p["learning_rate"], lstm_hidden_size=p["hidden"],
            lstm_n_layers=p["layers"], lstm_dropout=p["dropout"], max_steps=p["max_steps"],
        )
        return c

    def objective(trial):
        p = {
            "input_size": trial.suggest_categorical("input_size", [6, 9, 12]),
            "learning_rate": trial.suggest_float("learning_rate", 3e-4, 3e-3, log=True),
            "hidden": trial.suggest_categorical("hidden", [32, 64, 128]),
            "layers": trial.suggest_categorical("layers", [1, 2]),
            "dropout": trial.suggest_float("dropout", 0.0, 0.4),
            "max_steps": trial.suggest_categorical("max_steps", [300, 600, 900]),
        }
        cv = run_deepar(df, static, to_cfg(base, p), h, nw, seed=1)
        iv = interval_metrics(cv)
        trial.set_user_attr("coverage", iv["coverage"])
        return iv["pinball_lo"] + iv["pinball_median"] + iv["pinball_hi"]

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=0))
    study.enqueue_trial({"input_size": 12, "learning_rate": 1e-3, "hidden": 64, "layers": 2, "dropout": 0.1, "max_steps": 300})
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    _save(study, base, to_cfg, "deepar")


def tune_deepsurv(X_tr, d_tr, e_tr, X_va, d_va, e_va, base, n_trials=12, seed=0):
    """Return the best DeepSurv config for ONE outer split, scored by validation C-index."""
    from src.evaluation.survival_metrics import c_index
    from src.models.deepsurv import DeepSurv

    def to_cfg(b, p):
        c = copy.deepcopy(b)
        c.update(
            hidden=[p["width"]] * p["layers"], dropout=p["dropout"], learning_rate=p["learning_rate"],
            weight_decay=p["weight_decay"], batch_size=p["batch_size"],
        )
        return c

    def objective(trial):
        p = {
            "width": trial.suggest_categorical("width", [16, 32, 64, 128]),
            "layers": trial.suggest_int("layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.0, 0.5),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
            "weight_decay": trial.suggest_float("weight_decay", 1e-5, 1e-2, log=True),
            "batch_size": trial.suggest_categorical("batch_size", [64, 128, 256]),
        }
        try:
            m = DeepSurv(to_cfg(base, p), seed).fit(X_tr, d_tr, e_tr, X_va, d_va, e_va)
            return c_index(d_va, e_va, m.risk(X_va))
        except Exception:
            return 0.5

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return to_cfg(base, study.best_params), study.best_value


if __name__ == "__main__":
    which = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    {"nhits": tune_nhits, "deepar": tune_deepar}[which](*([n] if n else []))
