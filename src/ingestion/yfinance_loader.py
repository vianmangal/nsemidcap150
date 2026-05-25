from __future__ import annotations

from datetime import date, timedelta
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

from utils.paths import ensure_dir, safe_filename

LOGGER = logging.getLogger(__name__)


def normalize_symbol(symbol: str) -> tuple[str, str]:
    cleaned = symbol.strip().upper()
    if cleaned.endswith(".NS"):
        return cleaned[:-3], cleaned
    return cleaned, f"{cleaned}.NS"


def load_yfinance_history(
    symbol: str,
    data_dir: Path,
    start: date | None = None,
    end: date | None = None,
    force_full: bool = False,
) -> pd.DataFrame:
    data_dir = Path(data_dir)
    processed_dir = ensure_dir(data_dir / "processed" / "yfinance")

    base_symbol, yf_symbol = normalize_symbol(symbol)
    safe_symbol = safe_filename(base_symbol)
    processed_path = processed_dir / f"{safe_symbol}.parquet"

    existing = None
    if processed_path.exists():
        existing = pd.read_parquet(processed_path)
        if not existing.empty:
            if "date" not in existing.columns:
                LOGGER.warning("Processed yfinance data missing date column for %s", base_symbol)
                existing = None
            else:
                existing["date"] = pd.to_datetime(existing["date"], errors="coerce")

    start_date = start
    if existing is not None and not existing.empty and not force_full:
        last_date = existing["date"].max().date()
        next_date = last_date + timedelta(days=1)
        if start_date is None or start_date <= last_date:
            start_date = next_date

    if end is not None and start_date is not None and start_date > end:
        LOGGER.info("No new data for %s", base_symbol)
        return existing if existing is not None else pd.DataFrame()

    LOGGER.info("Downloading yfinance data for %s", yf_symbol)
    df = yf.download(
        yf_symbol,
        start=start_date.isoformat() if start_date else None,
        end=end.isoformat() if end else None,
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        LOGGER.warning("No yfinance data returned for %s", yf_symbol)
        return existing if existing is not None else pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.reset_index()
    df = df.rename(
        columns={
            "Date": "date",
            "Datetime": "date",
            "index": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    if "date" not in df.columns:
        raise ValueError("Expected date column missing from yfinance output")

    df["symbol"] = base_symbol
    df["turnover"] = df["close"] * df["volume"]

    df = df[["symbol", "open", "high", "low", "close", "volume", "turnover", "date"]]

    combined = df
    if existing is not None and not existing.empty:
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["symbol", "date"], keep="last")

    combined = combined.sort_values(["symbol", "date"]).reset_index(drop=True)
    combined.to_parquet(processed_path, index=False)
    return combined
