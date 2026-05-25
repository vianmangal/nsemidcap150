from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from indicators.car import CarConfig, compute_car
from utils.paths import ensure_dir, safe_filename

LOGGER = logging.getLogger(__name__)


def _symbol_file_name(symbol: str) -> str:
    return f"{safe_filename(symbol.strip().upper())}.parquet"


def load_indicator_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def compute_car_for_indicators(
    data_dir: Path,
    output_dir: Path | None = None,
    symbols: Iterable[str] | None = None,
    config: CarConfig | None = None,
) -> dict[str, Path]:
    data_dir = Path(data_dir)
    indicator_dir = data_dir / "processed" / "indicators"
    if not indicator_dir.exists():
        LOGGER.warning("No indicator data found at %s", indicator_dir)
        return {}

    if output_dir is None:
        output_dir = data_dir / "processed" / "car"
    output_dir = ensure_dir(Path(output_dir))

    files: list[Path]
    if symbols:
        files = [indicator_dir / _symbol_file_name(symbol) for symbol in symbols]
    else:
        files = sorted(indicator_dir.glob("*.parquet"))

    car_config = config or CarConfig()
    car_config.validate()

    results: dict[str, Path] = {}
    for path in files:
        if not path.exists():
            LOGGER.warning("Missing indicator file: %s", path)
            continue
        df = load_indicator_parquet(path)
        enriched = compute_car(df, car_config)
        out_path = output_dir / path.name
        enriched.to_parquet(out_path, index=False)
        symbol_key = enriched["symbol"].iloc[0] if "symbol" in enriched.columns else path.stem
        results[str(symbol_key)] = out_path

    return results
