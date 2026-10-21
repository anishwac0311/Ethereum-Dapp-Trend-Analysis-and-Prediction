"""Run all EDA scripts in order."""
from __future__ import annotations

import os
import runpy
import sys
import time
from pathlib import Path

# Stable non-interactive plotting on Windows
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

SCRIPTS = [
    "01_data_quality.py",
    "02_ecosystem_evolution.py",
    "03_lifecycle_clustering.py",
    "04_adoption_retention.py",
    "05_pre_adoption_dynamics.py",
    "06_predictive_eda.py",
]


def main() -> None:
    eda = Path(__file__).resolve().parent
    sys.path.insert(0, str(eda))
    t0 = time.time()
    for name in SCRIPTS:
        path = eda / name
        print("\n" + "=" * 60)
        print(f"Running {name}")
        print("=" * 60)
        t1 = time.time()
        runpy.run_path(str(path), run_name="__main__")
        print(f"Finished {name} in {time.time() - t1:.1f}s")
    print(f"\nAll EDA scripts done in {time.time() - t0:.1f}s")
    print("See eda/EDA_FINDINGS.md for the narrative summary.")


if __name__ == "__main__":
    main()
