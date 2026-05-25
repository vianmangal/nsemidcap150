from __future__ import annotations

from datetime import date, timedelta
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from .bhavcopy import load_bhavcopy_for_date
from .yfinance_loader import load_yfinance_history

LOGGER = logging.getLogger(__name__)


def update_bhavcopy_for_date(as_of: date, data_dir: Path) -> pd.DataFrame:
    return load_bhavcopy_for_date(as_of, data_dir)


def update_bhavcopy_range(start: date, end: date, data_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    current = start
    while current <= end:
        try:
            frames.append(load_bhavcopy_for_date(current, data_dir))
        except Exception as exc:
            LOGGER.warning("Failed bhavcopy for %s: %s", current, exc)
        current += timedelta(days=1)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def update_yfinance_history(
    symbols: Iterable[str],
    data_dir: Path,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        clean_symbol = symbol.strip()
        if not clean_symbol:
            continue
        try:
            results[clean_symbol] = load_yfinance_history(
                clean_symbol,
                data_dir,
                start=start,
                end=end,
            )
        except Exception as exc:
            LOGGER.warning("Failed yfinance for %s: %s", clean_symbol, exc)
    return results
