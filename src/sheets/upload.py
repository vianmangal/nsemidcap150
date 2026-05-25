from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Union

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _load_service_account(creds: str):
    """Load service account from a filepath or JSON string."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        path = Path(creds)
        if path.exists():
            # use file path
            from google.oauth2.service_account import Credentials

            with open(path, "r") as fh:
                data = json.load(fh)
            return Credentials.from_service_account_info(data, scopes=scopes)
        else:
            # try parse as JSON
            data = json.loads(creds)
            from google.oauth2.service_account import Credentials
            return Credentials.from_service_account_info(data, scopes=scopes)
    except Exception as exc:
        LOGGER.exception("Failed to load service account: %s", exc)
        raise


def publish_final_to_sheets(csv_path: Union[str, Path], sheet_id: str, service_account_json: str, worksheet_title: str | None = None) -> None:
    """Publish a final screener CSV to Google Sheets.

    - `csv_path`: path to CSV file
    - `sheet_id`: Google Sheets spreadsheet ID
    - `service_account_json`: path to service account JSON file or JSON string
    """
    try:
        import gspread
    except Exception:
        LOGGER.exception("gspread is not installed; cannot publish to Google Sheets")
        raise

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    creds = _load_service_account(service_account_json)
    client = gspread.authorize(creds)

    # Open spreadsheet
    sh = client.open_by_key(sheet_id)

    # Choose or create worksheet
    if worksheet_title:
        try:
            ws = sh.worksheet(worksheet_title)
        except Exception:
            rows = max(1000, len(df) + 10)
            cols = max(26, len(df.columns))
            ws = sh.add_worksheet(title=worksheet_title, rows=str(rows), cols=str(cols))
    else:
        try:
            ws = sh.sheet1
        except Exception:
            ws = sh.add_worksheet(title="Final Screener", rows=1000, cols=26)

    # Prepare values: header + rows
    values = [list(df.columns)] + df.fillna("").astype(str).values.tolist()

    # Clear and update
    ws.clear()
    ws.update("A1", values)
