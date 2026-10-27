"""Shared paths and helpers for the sustained-success model package."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
MODEL = Path(__file__).resolve().parent
DATA = ROOT / "dapp_data_v2"
FIG = MODEL / "figures"
TABLES = MODEL / "tables"
EDA = ROOT / "eda"

for d in (FIG, TABLES):
    d.mkdir(parents=True, exist_ok=True)


def _load_eda_common():
    path = EDA / "common.py"
    spec = importlib.util.spec_from_file_location("eda_common", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_eda = _load_eda_common()
load_panel = _eda.load_panel
load_static = _eda.load_static
load_lifecycle = _eda.load_lifecycle
load_category_month = _eda.load_category_month
load_cohort_retention = _eda.load_cohort_retention
annotate_lifecycle = _eda.annotate_lifecycle
PANEL_START = _eda.PANEL_START
PANEL_END = _eda.PANEL_END


def setup_style() -> None:
    sns.set_theme(style="whitegrid", context="talk", font_scale=0.85)
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def savefig(fig: plt.Figure, name: str) -> Path:
    path = FIG / name
    if not path.suffix:
        path = path.with_suffix(".png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.relative_to(MODEL)}")
    return path


def savetable(df: pd.DataFrame, name: str) -> Path:
    path = TABLES / name
    if not path.suffix:
        path = path.with_suffix(".csv")
    df.to_csv(path, index=False)
    print(f"  saved {path.relative_to(MODEL)}")
    return path


def safe_log1p(x) -> np.ndarray:
    return np.log1p(np.clip(np.asarray(x, dtype=float), 0, None))
