"""Run the full modelling pipeline in order."""
from __future__ import annotations

import os
import runpy
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

SCRIPTS = [
    "labels.py",
    "wallet_features.py",   # cached after the first run; --refresh to rebuild
    "token_incentives/build_token_features.py",  # cached; first scan of S3 takes ~4h
    "features.py",
    "train_eval.py",
    "panel_forecast.py",    # forecaster sanity report + leakage check
    "robust_eval.py",       # pooled OOF, threshold grid, paired bootstrap
    "final_model.py",       # final blend + confidence bands (k=3, k=6)
    "predict.py",
]


def main() -> None:
    model = Path(__file__).resolve().parent
    sys.path.insert(0, str(model))
    t0 = time.time()
    for name in SCRIPTS:
        path = model / name
        print("\n" + "=" * 60)
        print(f"Running {name}")
        print("=" * 60)
        t1 = time.time()
        argv, sys.argv = sys.argv, [str(path)]  # each script uses its own defaults
        try:
            runpy.run_path(str(path), run_name="__main__")
        finally:
            sys.argv = argv
        print(f"Finished {name} in {time.time() - t1:.1f}s")
    print(f"\nAll model scripts done in {time.time() - t0:.1f}s")
    print("See model/MODEL_REPORT.md for the narrative summary.")


if __name__ == "__main__":
    main()
