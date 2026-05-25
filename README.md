# NSE Breakout Screener

Automated breakout stock screener for NSE data with a modular pipeline, Google Sheets output, and automation.

## Project Structure
```
src/
  automation/
  config/
  indicators/
  ingestion/
  screener/
  sheets/
  utils/
data/
  raw/
  processed/
  cache/
logs/
output/
main.py
requirements.txt
```

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy env file: `cp .env.example .env`
4. Run: `python main.py`

## Configuration
Set these in .env:

- LOG_LEVEL
- DATA_DIR
- GOOGLE_SHEETS_ID
- GOOGLE_SERVICE_ACCOUNT_JSON
- RUN_INGESTION
- BHAVCOPY_DATE
- YFINANCE_SYMBOLS
- YFINANCE_START
- YFINANCE_END
- RUN_RANKING
- RANK_DATE
- RANK_MODE
- TOP_N
- RUN_INDICATORS
- INDICATOR_SYMBOLS
- RUN_CAR
- CAR_SYMBOLS
- CAR_LOOKBACK
- CAR_RISE_SESSIONS
- RUN_FINAL
- FINAL_SYMBOLS
- FINAL_TAG

## Notes
Phase-specific modules will be added iteratively. See plan.md for the full roadmap.

## GitHub Actions Automation (Phase 8)
The workflow is in [.github/workflows/screener.yml](.github/workflows/screener.yml) and runs daily plus on manual trigger.

### Required GitHub Secrets
- `GOOGLE_SHEETS_ID`: Spreadsheet ID
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Full service account JSON content (not base64)

### Recommended GitHub Secrets
- `YFINANCE_SYMBOLS`: Comma-separated list of symbols (e.g., `RELIANCE,TCS`)
- `YFINANCE_END`: Optional end date (YYYY-MM-DD)

### Sheet Access
Share the Google Sheet with the service account email from your JSON (`client_email`).

### Schedule
Default schedule is daily at 01:30 UTC. Adjust the cron in [.github/workflows/screener.yml](.github/workflows/screener.yml) if needed.
# nsemidcap150
