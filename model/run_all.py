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
    "features.py",
    "train_eval.py",
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
        runpy.run_path(str(path), run_name="__main__")
        print(f"Finished {name} in {time.time() - t1:.1f}s")
    print(f"\nAll model scripts done in {time.time() - t0:.1f}s")
    print("See model/MODEL_REPORT.md for the narrative summary.")


if __name__ == "__main__":
    main()
