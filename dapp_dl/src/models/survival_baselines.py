"""Cox PH baseline (lifelines, ridge-penalised) on the same features and splits as DeepSurv."""
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

from src.models.deepsurv import Scaler


class CoxBaseline:
    def __init__(self, penalizer=0.1):
        self.penalizer = penalizer

    def fit(self, X_tr, d_tr, e_tr):
        # lifelines cannot standardise constant columns (e.g. a rare category absent from the
        # training split), so keep only columns that vary in the training data
        self.keep = np.where(X_tr.std(0) > 0)[0]
        self.scaler = Scaler().fit(X_tr)
        df = self._df(X_tr)
        df["duration"], df["event"] = d_tr, e_tr
        self.cph = CoxPHFitter(penalizer=self.penalizer).fit(df, "duration", "event")
        return self

    def _df(self, X):
        Z = self.scaler.transform(X)[:, self.keep]
        return pd.DataFrame(Z, columns=[f"x{i}" for i in self.keep])

    def risk(self, X):
        return self.cph.predict_log_partial_hazard(self._df(X)).to_numpy().reshape(-1)

    def survival(self, X):
        s = self.cph.predict_survival_function(self._df(X))
        s.columns = range(s.shape[1])
        return s
