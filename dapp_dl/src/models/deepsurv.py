"""DeepSurv: Cox proportional-hazards model with an MLP risk function (pycox CoxPH).

Why: handles right-censoring (dApps still alive at the end of the data) and learns non-linear
interactions among launch/early-life features. Outputs a log-risk score per dApp and, with the
Breslow baseline hazard, a full survival curve S(t | x).
"""
import numpy as np
import torch
import torchtuples as tt
from pycox.models import CoxPH


class Scaler:
    def fit(self, X):
        self.mu = X.mean(0)
        self.sd = X.std(0)
        self.sd[self.sd == 0] = 1.0
        return self

    def transform(self, X):
        return ((X - self.mu) / self.sd).astype("float32")


class DeepSurv:
    def __init__(self, cfg, seed=0):
        self.cfg, self.seed = cfg, seed

    def fit(self, X_tr, d_tr, e_tr, X_va, d_va, e_va):
        c = self.cfg
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        self.scaler = Scaler().fit(X_tr)
        x_tr, x_va = self.scaler.transform(X_tr), self.scaler.transform(X_va)
        net = tt.practical.MLPVanilla(
            x_tr.shape[1], list(c["hidden"]), 1, c["batch_norm"], c["dropout"], output_bias=False
        )
        self.model = CoxPH(net, tt.optim.Adam(lr=c["learning_rate"], weight_decay=c["weight_decay"]))
        self.log = self.model.fit(
            x_tr,
            (d_tr.astype("float32"), e_tr.astype("float32")),
            batch_size=c["batch_size"],
            epochs=c["epochs"],
            callbacks=[tt.callbacks.EarlyStopping(patience=c["patience"])],
            verbose=False,
            val_data=(x_va, (d_va.astype("float32"), e_va.astype("float32"))),
        )
        self.model.compute_baseline_hazards()
        return self

    def risk(self, X):
        """Log relative hazard; higher = earlier event."""
        return self.model.predict(self.scaler.transform(X)).reshape(-1)

    def survival(self, X):
        """DataFrame of S(t | x): index = time grid (months), columns = subjects 0..n-1."""
        return self.model.predict_surv_df(self.scaler.transform(X))
