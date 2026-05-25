from __future__ import annotations

from datetime import date, timedelta
import io
import logging
from pathlib import Path

import pandas as pd

from .cache import FileCache
from .request_manager import RequestManager, HttpStatusError, RequestError
from utils.paths import ensure_dir

LOGGER = logging.getLogger(__name__)

BHAVCOPY_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv"
BHAVCOPY_FALLBACK_DAYS = 7


def bhavcopy_url(as_of: date) -> str:
    return BHAVCOPY_URL.format(date=as_of.strftime("%d%m%Y"))


def is_valid_bhavcopy(content: bytes) -> bool:
    if not content:
        return False
    snippet = content[:2048]
    try:
        text = snippet.decode("utf-8", errors="ignore").upper()
    except Exception:
        return False
    if "<HTML" in text or "ACCESS DENIED" in text:
        return False
    return "SYMBOL" in text and "SERIES" in text


def download_bhavcopy_csv(
    as_of: date,
    data_dir: Path,
    request_manager: RequestManager | None = None,
) -> tuple[bytes, date]:
    data_dir = Path(data_dir)
    cache_dir = ensure_dir(data_dir / "cache" / "bhavcopy")
    cache = FileCache(cache_dir)

    manager = request_manager or RequestManager()
    manager.prime_nse_session()

    for offset in range(0, BHAVCOPY_FALLBACK_DAYS + 1):
        candidate = as_of - timedelta(days=offset)
        cache_key = f"sec_bhavdata_full_{candidate:%d%m%Y}.csv"

        cached = cache.get_bytes(cache_key)
        if cached is not None:
            LOGGER.info("Using cached bhavcopy for %s", candidate)
            return cached, candidate

        url = bhavcopy_url(candidate)
        LOGGER.info("Downloading bhavcopy: %s", url)
        try:
            response = manager.get(url, headers={"Referer": "https://www.nseindia.com/"})
            content = response.content
            if not is_valid_bhavcopy(content):
                LOGGER.warning("Invalid bhavcopy content for %s", candidate)
                continue
        except HttpStatusError as exc:
            if exc.status_code == 404:
                continue
            LOGGER.warning("Bhavcopy download failed for %s: %s", candidate, exc)
            continue
        except RequestError as exc:
            LOGGER.warning("Bhavcopy download error for %s: %s", candidate, exc)
            continue
        except Exception as exc:
            LOGGER.warning("Unexpected bhavcopy error for %s: %s", candidate, exc)
            continue

        cache.write_bytes(cache_key, content)
        if candidate != as_of:
            LOGGER.info("Fallback bhavcopy date used: %s", candidate)
        return content, candidate

    raise FileNotFoundError(
        f"No bhavcopy found for {as_of} within {BHAVCOPY_FALLBACK_DAYS} days"
    )


def save_raw_bhavcopy(content: bytes, as_of: date, data_dir: Path) -> Path:
    raw_dir = ensure_dir(data_dir / "raw" / "bhavcopy")
    raw_path = raw_dir / f"bhavcopy_{as_of:%Y-%m-%d}.csv"
    raw_path.write_bytes(content)
    return raw_path


def read_raw_bhavcopy(as_of: date, data_dir: Path) -> bytes | None:
    raw_path = Path(data_dir) / "raw" / "bhavcopy" / f"bhavcopy_{as_of:%Y-%m-%d}.csv"
    if raw_path.exists():
        return raw_path.read_bytes()
    return None


def parse_bhavcopy(content: bytes, as_of: date) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [col.strip() for col in df.columns]

    if "SERIES" in df.columns:
        df = df[df["SERIES"].astype(str).str.strip().str.upper() == "EQ"]

    rename_map = {
        "SYMBOL": "symbol",
        "OPEN_PRICE": "open",
        "HIGH_PRICE": "high",
        "LOW_PRICE": "low",
        "CLOSE_PRICE": "close",
        "TOTTRDQTY": "volume",
        "TTL_TRD_QNTY": "volume",
        "TOTTRDVAL": "turnover",
        "TURNOVER_LACS": "turnover_lacs",
    }
    df = df.rename(columns=rename_map)

    if "turnover_lacs" in df.columns:
        df["turnover_lacs"] = pd.to_numeric(df["turnover_lacs"], errors="coerce")
        if "turnover" not in df.columns:
            df["turnover"] = df["turnover_lacs"] * 100000

    required = ["symbol", "open", "high", "low", "close", "volume", "turnover"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date"] = pd.to_datetime(as_of)

    df = df[["symbol", "open", "high", "low", "close", "volume", "turnover", "date"]]
    return df.dropna(subset=["symbol"]).reset_index(drop=True)


def save_bhavcopy_parquet(df: pd.DataFrame, as_of: date, data_dir: Path) -> Path:
    processed_dir = ensure_dir(data_dir / "processed" / "bhavcopy")
    processed_path = processed_dir / f"bhavcopy_{as_of:%Y-%m-%d}.parquet"
    df.to_parquet(processed_path, index=False)
    return processed_path


def load_bhavcopy_for_date(
    as_of: date,
    data_dir: Path,
    request_manager: RequestManager | None = None,
) -> pd.DataFrame:
    data_dir = Path(data_dir)
    processed_path = data_dir / "processed" / "bhavcopy" / f"bhavcopy_{as_of:%Y-%m-%d}.parquet"
    if processed_path.exists():
        LOGGER.info("Loading processed bhavcopy for %s", as_of)
        processed_df = pd.read_parquet(processed_path)
        if not processed_df.empty:
            return processed_df
        LOGGER.warning("Processed bhavcopy empty for %s; reloading raw", as_of)

    content, actual_date = download_bhavcopy_csv(
        as_of, data_dir, request_manager=request_manager
    )
    actual_processed = (
        data_dir / "processed" / "bhavcopy" / f"bhavcopy_{actual_date:%Y-%m-%d}.parquet"
    )
    if actual_processed.exists():
        LOGGER.info("Loading processed bhavcopy for %s", actual_date)
        processed_df = pd.read_parquet(actual_processed)
        if not processed_df.empty:
            return processed_df
        LOGGER.warning("Processed bhavcopy empty for %s; rebuilding", actual_date)

    raw_bytes = read_raw_bhavcopy(actual_date, data_dir)
    if raw_bytes is not None:
        content = raw_bytes

    save_raw_bhavcopy(content, actual_date, data_dir)
    df = parse_bhavcopy(content, actual_date)
    save_bhavcopy_parquet(df, actual_date, data_dir)
    return df
