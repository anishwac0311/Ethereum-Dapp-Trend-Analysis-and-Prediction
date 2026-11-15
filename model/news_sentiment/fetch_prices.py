"""ETH/USD weekly closes from Kraken's public OHLC endpoint (history back to 2015).

Used to keep *market momentum* separate from *news sentiment*: the model gets both, and
the ablation shows whether news adds anything beyond price.

Output: data/eth_weekly.csv, data/eth_monthly.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import DATA, fetch


def main() -> None:
    txt = fetch("https://api.kraken.com/0/public/OHLC?pair=ETHUSD&interval=10080", use_cache=False)
    if not txt:
        raise SystemExit("Kraken fetch failed")
    payload = json.loads(txt)
    if payload.get("error"):
        raise SystemExit(f"Kraken error: {payload['error']}")
    key = next(k for k in payload["result"] if k != "last")
    rows = payload["result"][key]
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["date"] = pd.to_datetime(df["ts"], unit="s")
    for c in ["open", "high", "low", "close", "vwap", "volume"]:
        df[c] = df[c].astype(float)
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df.to_csv(DATA / "eth_weekly.csv", index=False)

    m = df.set_index("date")["close"].resample("MS").last().to_frame("eth_close")
    m["eth_ret_1m"] = np.log(m["eth_close"]).diff()
    weekly_ret = np.log(df.set_index("date")["close"]).diff()
    m["eth_vol_1m"] = weekly_ret.resample("MS").std() * np.sqrt(52)
    m.index = m.index.to_period("M").astype(str)
    m.index.name = "month"
    m.reset_index().to_csv(DATA / "eth_monthly.csv", index=False)
    print(f"saved eth_weekly.csv ({len(df)} weeks, {df['date'].min().date()} to {df['date'].max().date()})")
    print(f"saved eth_monthly.csv ({len(m)} months)")


if __name__ == "__main__":
    main()
