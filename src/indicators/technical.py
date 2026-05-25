from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _rolling_mean(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def add_indicators(
    df: pd.DataFrame,
    windows: Iterable[int] = (50, 100, 200),
) -> pd.DataFrame:
    if "close" not in df.columns:
        raise ValueError("Input dataframe must include a 'close' column")

    working = df.copy()
    if "date" in working.columns:
        working["date"] = pd.to_datetime(working["date"], errors="coerce")

    group_cols: list[str] = []
    sort_cols: list[str] = []
    if "symbol" in working.columns:
        group_cols.append("symbol")
        sort_cols.append("symbol")
    if "date" in working.columns:
        sort_cols.append("date")

    if sort_cols:
        working = working.sort_values(sort_cols)

    if group_cols:
        grouped = working.groupby(group_cols, dropna=False, sort=False)
        for window in windows:
            working[f"sma{window}"] = grouped["close"].transform(
                lambda series: _rolling_mean(series, window)
            )
    else:
        for window in windows:
            working[f"sma{window}"] = _rolling_mean(working["close"], window)

    working["cmp"] = working["close"]

    sma200 = working.get("sma200")
    if sma200 is not None:
        sma200 = sma200.replace(0, pd.NA)
        working["diff_from_200"] = ((working["cmp"] - sma200) / sma200) * 100
    else:
        working["diff_from_200"] = pd.NA

    bull = (
        (working["cmp"] > working.get("sma50"))
        & (working["cmp"] > working.get("sma100"))
        & (working["cmp"] > working.get("sma200"))
        & (working["diff_from_200"] <= 10)
    )
    bear = (
        (working["cmp"] < working.get("sma50"))
        & (working["cmp"] < working.get("sma100"))
        & (working["cmp"] < working.get("sma200"))
    )

    working["bull_run"] = bull.fillna(False)
    working["bear_run"] = bear.fillna(False)

    trend = pd.Series("Unconfirmed", index=working.index)
    trend = trend.mask(working["bull_run"], "Bull Run")
    trend = trend.mask(working["bear_run"], "Bear Run")
    working["trend"] = trend

    return working
