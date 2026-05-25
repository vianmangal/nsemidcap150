from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from utils.paths import ensure_dir, safe_filename

LOGGER = logging.getLogger(__name__)


def _symbol_file_name(symbol: str) -> str:
    return f"{safe_filename(symbol.strip().upper())}.parquet"


def load_car_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Ensure a symbol column exists — some CAR parquet files are stored without
    # the `symbol` column (symbol encoded in filename). Use the file stem
    # as the symbol when missing so downstream filtering works.
    if "symbol" not in df.columns:
        df["symbol"] = path.stem
    return df


def select_latest(df: pd.DataFrame) -> pd.DataFrame:
    if "symbol" in df.columns and "date" in df.columns:
        df = df.sort_values(["symbol", "date"])
        return df.groupby("symbol", as_index=False).tail(1)
    if "date" in df.columns:
        return df.sort_values(["date"]).tail(1)
    return df


def filter_breakouts(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "symbol",
        "cmp",
        "volume",
        "turnover",
        "sma50",
        "sma100",
        "sma200",
        "diff_from_200",
        "car_signal",
        "bull_run",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    working = df.copy()
    working["diff_from_200"] = pd.to_numeric(working["diff_from_200"], errors="coerce")

    filtered = working[
        (working["bull_run"] == True)
        & (working["diff_from_200"] <= 10)
        & (working["car_signal"] == "BUY_AVERAGE_OUT")
    ]

    return filtered


def format_outputs(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "symbol",
        "cmp",
        "volume",
        "turnover",
        "sma50",
        "sma100",
        "sma200",
        "diff_from_200",
        "car_signal",
    ]
    available = [col for col in columns if col in df.columns]
    return df[available]


def save_outputs(df: pd.DataFrame, output_dir: Path, tag: str) -> dict[str, Path]:
    output_dir = ensure_dir(Path(output_dir))
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    csv_path = output_dir / f"final_screener_{tag}_{timestamp}.csv"
    json_path = output_dir / f"final_screener_{tag}_{timestamp}.json"
    excel_path = output_dir / f"final_screener_{tag}_{timestamp}.xlsx"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records")
    df.to_excel(excel_path, index=False)

    return {"csv": csv_path, "json": json_path, "excel": excel_path}


def run_final_screener(
    data_dir: Path,
    output_dir: Path,
    symbols: Iterable[str] | None = None,
    tag: str = "daily",
) -> tuple[pd.DataFrame, dict[str, Path]]:
    data_dir = Path(data_dir)
    car_dir = data_dir / "processed" / "car"
    if not car_dir.exists():
        raise FileNotFoundError(f"CAR data not found at {car_dir}")

    files: list[Path]
    if symbols:
        files = [car_dir / _symbol_file_name(symbol) for symbol in symbols]
    else:
        files = sorted(car_dir.glob("*.parquet"))

    frames: list[pd.DataFrame] = []
    for path in files:
        if not path.exists():
            LOGGER.warning("Missing CAR file: %s", path)
            continue
        df = load_car_parquet(path)
        df = select_latest(df)
        frames.append(df)

    if not frames:
        raise ValueError("No CAR data available for final screener")

    combined = pd.concat(frames, ignore_index=True)
    filtered = filter_breakouts(combined)
    filtered = filtered.sort_values("turnover", ascending=False)

    formatted = format_outputs(filtered)
    outputs = save_outputs(formatted, output_dir=output_dir, tag=tag)

    return formatted, outputs
