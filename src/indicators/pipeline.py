from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from .technical import add_indicators
from utils.paths import ensure_dir, safe_filename

LOGGER = logging.getLogger(__name__)


def _symbol_file_name(symbol: str) -> str:
    return f"{safe_filename(symbol.strip().upper())}.parquet"


def load_yfinance_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    else:
        normalized_cols: list[str] = []
        for col in df.columns:
            if isinstance(col, str) and col.startswith("(") and col.endswith(")"):
                try:
                    parsed = ast.literal_eval(col)
                except (SyntaxError, ValueError):
                    parsed = None
                if isinstance(parsed, tuple) and parsed:
                    normalized_cols.append(str(parsed[0]))
                    continue
            normalized_cols.append(str(col))
        df.columns = normalized_cols
    df = df.rename(
        columns={
            "Date": "date",
            "Datetime": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "close" not in df.columns:
        raise ValueError(f"Missing close column. Columns: {sorted(df.columns)}")
    return df


def compute_indicators_for_yfinance(
    data_dir: Path,
    output_dir: Path | None = None,
    symbols: Iterable[str] | None = None,
) -> dict[str, Path]:
    data_dir = Path(data_dir)
    yfinance_dir = data_dir / "processed" / "yfinance"
    if not yfinance_dir.exists():
        LOGGER.warning("No yfinance data found at %s", yfinance_dir)
        return {}

    if output_dir is None:
        output_dir = data_dir / "processed" / "indicators"
    output_dir = ensure_dir(Path(output_dir))

    files: list[Path]
    if symbols:
        files = [yfinance_dir / _symbol_file_name(symbol) for symbol in symbols]
    else:
        files = sorted(yfinance_dir.glob("*.parquet"))

    results: dict[str, Path] = {}
    for path in files:
        if not path.exists():
            LOGGER.warning("Missing yfinance file: %s", path)
            continue
        try:
            df = load_yfinance_parquet(path)
        except ValueError as exc:
            LOGGER.warning("Skipping %s: %s", path.name, exc)
            continue
        enriched = add_indicators(df)
        out_path = output_dir / path.name
        enriched.to_parquet(out_path, index=False)
        if "symbol" in enriched.columns and not enriched.empty:
            symbol_key = enriched["symbol"].iloc[0]
        else:
            symbol_key = path.stem
        results[str(symbol_key)] = out_path

    return results
