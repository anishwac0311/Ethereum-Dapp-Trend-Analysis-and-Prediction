"""N-HiTS: global point forecaster over all dApps (neuralforecast).

Why: one MLP-stack model shares strength across ~250 short series, and multi-rate pooling
handles both the fast launch ramp and the slow decay. Uses the full covariate set:
  static (category, token flag, contracts), known-future (months_since_launch),
  historical (new wallets, gas, tx/wallet, retention, top-10 share, protocols per tx).
Loss: MAE on log1p(active_wallets).
"""
from neuralforecast import NeuralForecast
from neuralforecast.losses.pytorch import MAE
from neuralforecast.models import NHITS

from src.data.build_forecast_panel import FUTR, HIST, static_cols


def build_nhits(static, cfg, h, seed=1):
    return NHITS(
        h=h,
        input_size=cfg["input_size"],
        loss=MAE(),
        max_steps=cfg["max_steps"],
        learning_rate=cfg["learning_rate"],
        batch_size=cfg["batch_size"],
        windows_batch_size=cfg["windows_batch_size"],
        val_check_steps=cfg["val_check_steps"],
        early_stop_patience_steps=cfg["early_stop_patience_steps"],
        n_pool_kernel_size=cfg["n_pool_kernel_size"],
        n_freq_downsample=cfg["n_freq_downsample"],
        mlp_units=cfg["mlp_units"],
        dropout_prob_theta=cfg["dropout_prob_theta"],
        scaler_type=cfg["scaler_type"],
        futr_exog_list=FUTR,
        hist_exog_list=HIST,
        stat_exog_list=static_cols(static),
        start_padding_enabled=True,  # keep young dApps whose history is shorter than input_size
        random_seed=seed,
        enable_progress_bar=False,
        enable_model_summary=False,
        logger=False,
        accelerator="cpu",
    )


def run_nhits(df, static, cfg, h, n_windows, seed=1, step_size=None):
    model = build_nhits(static, cfg, h, seed)
    nf = NeuralForecast(models=[model], freq="MS")
    cv = nf.cross_validation(
        df=df, static_df=static, n_windows=n_windows, step_size=step_size or h, val_size=h, refit=True
    )
    return cv.rename(columns={"NHITS": "NHITS"})
