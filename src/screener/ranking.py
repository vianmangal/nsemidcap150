from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from ingestion.bhavcopy import load_bhavcopy_for_date
from utils.paths import ensure_dir

LOGGER = logging.getLogger(__name__)

EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "ETF",
    "GOLD",
    "LIQUID",
    "BEES",
    "SILVER",
    "BOND",
)


def filter_excluded_symbols(df: pd.DataFrame) -> pd.DataFrame:
    symbols = df["symbol"].astype(str).str.upper()
    pattern = "|".join(EXCLUDE_KEYWORDS)
    return df[~symbols.str.contains(pattern, regex=True, na=False)]


def rank_top_stocks(
    df: pd.DataFrame,
    mode: str,
    top_n: int = 250,
) -> pd.DataFrame:
    mode = mode.strip().lower()
    if mode not in {"volume", "turnover"}:
        raise ValueError("mode must be 'volume' or 'turnover'")

    required = {"symbol", "close", "volume", "turnover"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    working = df.copy()
    working["symbol"] = working["symbol"].astype(str).str.strip()
    working = filter_excluded_symbols(working)

    for col in ["close", "volume", "turnover"]:
        working[col] = pd.to_numeric(working[col], errors="coerce")

    working = working.dropna(subset=["symbol", mode])
    working = working.sort_values(by=mode, ascending=False)
    ranked = working.head(top_n).copy()
    ranked["rank"] = range(1, len(ranked) + 1)

    columns = ["symbol", "close", "volume", "turnover", "rank"]
    return ranked[columns]


def save_ranked_csv(
    ranked: pd.DataFrame,
    output_dir: Path,
    as_of: date,
    mode: str,
) -> Path:
    output_dir = ensure_dir(Path(output_dir))
    filename = f"top_250_{mode}_{as_of:%Y-%m-%d}.csv"
    output_path = output_dir / filename
    ranked.to_csv(output_path, index=False)
    return output_path


def rank_from_bhavcopy(
    as_of: date,
    data_dir: Path,
    mode: str,
    top_n: int,
    output_dir: Path,
) -> tuple[pd.DataFrame, Path]:
    df = load_bhavcopy_for_date(as_of, data_dir)
    LOGGER.info("Ranking %s rows from bhavcopy", len(df))
    ranked = rank_top_stocks(df, mode=mode, top_n=top_n)
    output_path = save_ranked_csv(ranked, output_dir=output_dir, as_of=as_of, mode=mode)
    return ranked, output_path


def filter_keywords() -> Iterable[str]:
    return EXCLUDE_KEYWORDS
