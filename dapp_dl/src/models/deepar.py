"""DeepAR: probabilistic global forecaster (neuralforecast).

Why: gives a predictive distribution (Student-t on log1p wallets), so we can report interval
coverage and ask risk questions such as P(active wallets < threshold in k months).
The Student-t likelihood is robust to the heavy tails in dApp activity. Same covariates as
N-HiTS. Output columns: DeepAR (mean), DeepAR-median, DeepAR-lo-80, DeepAR-hi-80.
"""
from neuralforecast import NeuralForecast
from neuralforecast.losses.pytorch import DistributionLoss
from neuralforecast.models import DeepAR

from src.data.build_forecast_panel import FUTR, HIST, static_cols


def build_deepar(static, cfg, h, seed=1):
    return DeepAR(
        h=h,
        input_size=cfg["input_size"],
        lstm_n_layers=cfg["lstm_n_layers"],
        lstm_hidden_size=cfg["lstm_hidden_size"],
        lstm_dropout=cfg["lstm_dropout"],
        trajectory_samples=cfg["trajectory_samples"],
        loss=DistributionLoss(distribution=cfg["distribution"], level=cfg["level"]),
        max_steps=cfg["max_steps"],
        learning_rate=cfg["learning_rate"],
        batch_size=cfg["batch_size"],
        windows_batch_size=cfg["windows_batch_size"],
        val_check_steps=cfg["val_check_steps"],
        early_stop_patience_steps=cfg["early_stop_patience_steps"],
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


def run_deepar(df, static, cfg, h, n_windows, seed=1, step_size=None):
    model = build_deepar(static, cfg, h, seed)
    nf = NeuralForecast(models=[model], freq="MS")
    return nf.cross_validation(
        df=df, static_df=static, n_windows=n_windows, step_size=step_size or h, val_size=h, refit=True
    )
