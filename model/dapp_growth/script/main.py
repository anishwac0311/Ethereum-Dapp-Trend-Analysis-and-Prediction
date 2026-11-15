"""Q4 growth: build the samples and checks once, run the survival and growth-curve analyses, then build
candidate model features from what they show.

    python script/main.py
"""
from __future__ import annotations

import os

# Thousands of tiny curve fits run faster on one thread than with numpy's thread pool
for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(var, "1")

import curves
import features
import samples
import survival
from common import read_growth_dapps, read_growth_series, read_panel, setup_style


def main() -> None:
    setup_style()
    print("== samples ==")
    samples.run(read_panel())

    dapps = read_growth_dapps()
    print("\n== time to 5k and 10k ==")
    survival.run(dapps)
    print("\n== growth curves ==")
    curves.run(dapps, read_growth_series(dapps))
    print("\n== candidate features ==")
    features.run(read_panel())


if __name__ == "__main__":
    main()
