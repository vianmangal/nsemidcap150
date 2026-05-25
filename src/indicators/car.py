from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CarConfig:
    lookback_days: int = 252
    rise_sessions: int = 10

    def validate(self) -> None:
        if self.lookback_days <= 1:
            raise ValueError("CAR lookback_days must be > 1")
        if self.rise_sessions <= 1:
            raise ValueError("CAR rise_sessions must be > 1")


def compute_car(df: pd.DataFrame, config: CarConfig) -> pd.DataFrame:
    if "close" not in df.columns:
        raise ValueError("Input dataframe must include a 'close' column")

    working = df.copy()
    if "date" in working.columns:
        working["date"] = pd.to_datetime(working["date"], errors="coerce")
        working = working.sort_values(["date"])

    if "symbol" in working.columns:
        group_cols = ["symbol"]
    else:
        group_cols = []

    def apply_group(group: pd.DataFrame) -> pd.DataFrame:
        close = group["close"].astype(float)
        rolling_high = close.rolling(window=config.lookback_days, min_periods=1).max()
        distance = ((close - rolling_high) / rolling_high) * 100
        car_value = distance.rolling(window=config.rise_sessions, min_periods=1).mean()

        rises = car_value.diff().gt(0).rolling(window=config.rise_sessions).sum()
        signal = rises.ge(config.rise_sessions - 1)

        group = group.copy()
        group["car_value"] = car_value
        group["car_signal"] = signal.map(
            {True: "BUY_AVERAGE_OUT", False: "AVOID_HOLD"}
        ).fillna("AVOID_HOLD")
        return group

    if group_cols:
        enriched = working.groupby(group_cols, dropna=False, sort=False).apply(apply_group)
        enriched = enriched.reset_index(drop=True)
    else:
        enriched = apply_group(working)

    return enriched
