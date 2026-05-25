from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")).resolve()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RUN_INGESTION = os.getenv("RUN_INGESTION", "0") == "1"
BHAVCOPY_DATE = os.getenv("BHAVCOPY_DATE", "").strip()
YFINANCE_SYMBOLS = os.getenv("YFINANCE_SYMBOLS", "").strip()
YFINANCE_START = os.getenv("YFINANCE_START", "").strip()
YFINANCE_END = os.getenv("YFINANCE_END", "").strip()
RUN_RANKING = os.getenv("RUN_RANKING", "0") == "1"
RANK_DATE = os.getenv("RANK_DATE", "").strip()
RUN_INDICATORS = os.getenv("RUN_INDICATORS", "0") == "1"
INDICATOR_SYMBOLS = os.getenv("INDICATOR_SYMBOLS", "").strip()
RUN_CAR = os.getenv("RUN_CAR", "0") == "1"
CAR_SYMBOLS = os.getenv("CAR_SYMBOLS", "").strip()
CAR_LOOKBACK = os.getenv("CAR_LOOKBACK", "").strip()
CAR_RISE_SESSIONS = os.getenv("CAR_RISE_SESSIONS", "").strip()
RUN_FINAL = os.getenv("RUN_FINAL", "0") == "1"
FINAL_SYMBOLS = os.getenv("FINAL_SYMBOLS", "").strip()
FINAL_TAG = os.getenv("FINAL_TAG", "daily").strip() or "daily"
RUN_SHEETS = os.getenv("RUN_SHEETS", "0") == "1"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()


def configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def parse_date(value: str) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_bhavcopy_date(value: str) -> datetime.date:
    parsed = parse_date(value)
    if parsed:
        return parsed
    return (datetime.now(timezone.utc) - timedelta(days=1)).date()


def main() -> None:
    configure_logging()
    logger = logging.getLogger("screener")
    logger.info("Starting NSE breakout screener")
    logger.info("Data directory: %s", DATA_DIR)

    if RUN_INGESTION:
        from ingestion.pipeline import update_bhavcopy_for_date, update_yfinance_history

        target_date = resolve_bhavcopy_date(BHAVCOPY_DATE)
        if BHAVCOPY_DATE and parse_date(BHAVCOPY_DATE) is None:
            logger.warning("Invalid BHAVCOPY_DATE; using %s", target_date)

        bhav_df = update_bhavcopy_for_date(target_date, data_dir=DATA_DIR)
        logger.info("Bhavcopy rows: %s", len(bhav_df))

        if YFINANCE_SYMBOLS:
            symbols = [symbol.strip() for symbol in YFINANCE_SYMBOLS.split(",") if symbol.strip()]
            start = parse_date(YFINANCE_START)
            end = parse_date(YFINANCE_END)
            if YFINANCE_START and start is None:
                logger.warning("Invalid YFINANCE_START; ignoring it")
            if YFINANCE_END and end is None:
                logger.warning("Invalid YFINANCE_END; ignoring it")
            update_yfinance_history(symbols, data_dir=DATA_DIR, start=start, end=end)
    else:
        logger.info("Ingestion skipped. Set RUN_INGESTION=1 to fetch data.")

    if RUN_RANKING:
        from config.ranking import RankConfig
        from screener.ranking import rank_from_bhavcopy

        rank_config = RankConfig.from_env()
        rank_config.validate()

        rank_date = resolve_bhavcopy_date(RANK_DATE or BHAVCOPY_DATE)
        if (RANK_DATE or BHAVCOPY_DATE) and parse_date(RANK_DATE or BHAVCOPY_DATE) is None:
            logger.warning("Invalid RANK_DATE; using %s", rank_date)

        ranked, output_path = rank_from_bhavcopy(
            rank_date,
            data_dir=DATA_DIR,
            mode=rank_config.mode,
            top_n=rank_config.top_n,
            output_dir=PROJECT_ROOT / "output",
        )
        logger.info("Ranked rows: %s", len(ranked))
        logger.info("Ranking CSV: %s", output_path)
    else:
        logger.info("Ranking skipped. Set RUN_RANKING=1 to run phase 3.")

    if RUN_INDICATORS:
        from indicators.pipeline import compute_indicators_for_yfinance

        symbols = None
        if INDICATOR_SYMBOLS:
            symbols = [
                symbol.strip()
                for symbol in INDICATOR_SYMBOLS.split(",")
                if symbol.strip()
            ]
        outputs = compute_indicators_for_yfinance(DATA_DIR, symbols=symbols)
        logger.info("Indicator files: %s", len(outputs))
    else:
        logger.info("Indicators skipped. Set RUN_INDICATORS=1 to run phase 4.")

    if RUN_CAR:
        from indicators.car import CarConfig
        from indicators.car_pipeline import compute_car_for_indicators

        symbols = None
        if CAR_SYMBOLS:
            symbols = [
                symbol.strip()
                for symbol in CAR_SYMBOLS.split(",")
                if symbol.strip()
            ]

        lookback = None
        rise_sessions = None
        if CAR_LOOKBACK:
            try:
                lookback = int(CAR_LOOKBACK)
            except ValueError:
                logger.warning("Invalid CAR_LOOKBACK; using default")
        if CAR_RISE_SESSIONS:
            try:
                rise_sessions = int(CAR_RISE_SESSIONS)
            except ValueError:
                logger.warning("Invalid CAR_RISE_SESSIONS; using default")

        config = CarConfig(
            lookback_days=lookback or CarConfig.lookback_days,
            rise_sessions=rise_sessions or CarConfig.rise_sessions,
        )
        config.validate()

        outputs = compute_car_for_indicators(DATA_DIR, symbols=symbols, config=config)
        logger.info("CAR files: %s", len(outputs))
    else:
        logger.info("CAR skipped. Set RUN_CAR=1 to run phase 5.")

    if RUN_FINAL:
        from screener.final_screener import run_final_screener

        symbols = None
        if FINAL_SYMBOLS:
            symbols = [
                symbol.strip()
                for symbol in FINAL_SYMBOLS.split(",")
                if symbol.strip()
            ]

        final_df, outputs = run_final_screener(
            data_dir=DATA_DIR,
            output_dir=PROJECT_ROOT / "output",
            symbols=symbols,
            tag=FINAL_TAG,
        )
        logger.info("Final screener rows: %s", len(final_df))
        logger.info("Final screener outputs: %s", outputs)
    else:
        logger.info("Final screener skipped. Set RUN_FINAL=1 to run phase 6.")

    if RUN_SHEETS:
        try:
            if not GOOGLE_SHEETS_ID or not GOOGLE_SERVICE_ACCOUNT_JSON:
                logger.warning(
                    "Google Sheets credentials not configured. Set GOOGLE_SHEETS_ID and GOOGLE_SERVICE_ACCOUNT_JSON to enable sheet uploads."
                )
            else:
                from sheets.upload import publish_final_to_sheets
                # Upload main final screener CSV if present
                csv_path = outputs.get("csv") if "outputs" in locals() else None
                if csv_path and csv_path.exists():
                    publish_final_to_sheets(csv_path, GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_JSON)
                    logger.info("Uploaded final screener to Google Sheets: %s", GOOGLE_SHEETS_ID)
                else:
                    logger.info("No main final screener CSV to upload; continuing to check for relaxed outputs.")

                # Find and upload any relaxed outputs to separate worksheet tabs
                output_dir = PROJECT_ROOT / "output"
                relaxed_files = sorted(output_dir.glob("final_screener_relaxed_*.csv"))
                for p in relaxed_files:
                    try:
                        publish_final_to_sheets(p, GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_JSON, worksheet_title=p.stem)
                        logger.info("Uploaded relaxed screener to Google Sheets tab: %s", p.stem)
                    except Exception:
                        logger.exception("Failed to upload relaxed screener: %s", p)
        except Exception:
            logger.exception("Failed to publish to Google Sheets")


if __name__ == "__main__":
    main()
