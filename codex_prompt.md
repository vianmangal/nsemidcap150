# `plan.md`

````md
# NSE Breakout Screener Automation Plan

## Objective

Build an automated breakout stock screener inspired by Mahesh Kaushik's workflow using:

- Python
- GitHub Actions
- Google Sheets API
- NSE/Bhavcopy/YFinance Data
- Automated technical analysis
- Volume + turnover screening
- CAR-based filtering

---

# SYSTEM ARCHITECTURE

```text
Market Data
    ↓
Data Collector
    ↓
Raw Data Storage
    ↓
Indicator Engine
    ↓
Breakout Engine
    ↓
CAR Engine
    ↓
Final Screener
    ↓
Google Sheets / Dashboard
    ↓
Automation Scheduler
````

---

# PHASE 1 — PROJECT INITIALIZATION

## Goal

Set up clean scalable architecture.

## Folder Structure

```text
project/
│
├── config/
├── data/
│   ├── raw/
│   ├── processed/
│   └── cache/
│
├── indicators/
├── screener/
├── automation/
├── sheets/
├── utils/
├── logs/
├── output/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# CODEX PROMPT — PHASE 1

Create a scalable Python project structure for an automated NSE breakout screener.

Requirements:

* Modular architecture
* Separate:

  * data ingestion
  * indicators
  * screener logic
  * automation
  * Google Sheets integration
* Create folders:
  config, data/raw, data/cache, indicators, screener, automation, logs, output
* Generate:

  * requirements.txt
  * .env.example
  * README.md
  * starter main.py
* Use best practices for maintainability.

---

# PHASE 2 — MARKET DATA PIPELINE

## Goal

Build reliable stock data ingestion.

## IMPORTANT

DO NOT SCRAPE NSE HTML PAGES DIRECTLY.

Preferred sources:

* NSE bhavcopy
* yfinance
* Upstox API
* Zerodha API

## Required Data

* symbol
* open
* high
* low
* close
* volume
* turnover

---

# CODEX PROMPT — PHASE 2

Build a robust NSE market data ingestion system in Python.

Requirements:

* Use requests.Session()
* Add browser-like headers
* Implement retry logic
* Implement caching
* Use local storage to avoid repeated requests
* Download:

  * OHLCV data
  * volume
  * turnover
* Use yfinance for historical candles
* Use bhavcopy for daily NSE market data
* Save cleaned data into parquet files

Features:

* logging
* error handling
* incremental updates
* rate-limit protection
* randomized delays

Libraries:

* pandas
* requests
* yfinance
* pyarrow
* tenacity

Do NOT use Selenium unless absolutely necessary.

---

# PHASE 3 — TOP 250 STOCK ENGINE

## Goal

Select:

* top 250 by turnover

## Filters

Exclude:

* ETFs
* Gold ETFs
* Liquid ETFs
* Bonds
* Mutual fund symbols

---

# CODEX PROMPT — PHASE 3

Create a Python stock ranking engine.

Requirements:

* Rank NSE stocks by:

  
  1. turnover
* Allow switching modes using config
* Filter out:
  ETF, GOLD, LIQUID, BEES, SILVER, BOND
* Return top 250 stocks
* Save output as dataframe + CSV
* Add clean logging
* Create reusable functions

Output columns:

* symbol
* close
* volume
* turnover
* rank

---

# PHASE 4 — TECHNICAL INDICATOR ENGINE

## Goal

Calculate:

* SMA50
* SMA100
* SMA200
* CMP
* % difference from 200 DMA

---

# CODEX PROMPT — PHASE 4

Create a technical indicator engine in Python.

Requirements:

* Input:
  OHLCV dataframe
* Calculate:

  * SMA50
  * SMA100
  * SMA200
  * CMP
  * Difference from SMA200
* Use pandas only
* Vectorized operations
* Handle missing data safely

Add classification logic:

Bull Run:

* CMP > SMA50
* CMP > SMA100
* CMP > SMA200
* diff_from_200 <= 10

Bear Run:

* CMP < SMA50
* CMP < SMA100
* CMP < SMA200

Else:

* Unconfirmed

Return enriched dataframe.

---

# PHASE 5 — CAR ENGINE

## Goal

Implement cumulative average reversal logic.

---

# CODEX PROMPT — PHASE 5

Implement a CAR (Cumulative Average Reversal) engine in Python.

Logic:

* Calculate rolling cumulative average distance from 52-week high
* Detect reversal behavior
* If cumulative average rises continuously for 10 sessions:
  signal = BUY_AVERAGE_OUT
* Else:
  signal = AVOID_HOLD

Requirements:

* Vectorized pandas implementation
* Configurable lookback periods
* Clear documentation
* Separate reusable functions
* Add unit-testable structure

Output:

* car_value
* car_signal

---

# PHASE 6 — FINAL SCREENER ENGINE

## Goal

Generate final actionable stock list.

---

# CODEX PROMPT — PHASE 6

Build the final breakout screener engine.

Conditions:

* Bull Run == TRUE
* Difference from 200 DMA <= 10
* CAR signal == BUY_AVERAGE_OUT

Output columns:

* symbol
* CMP
* volume
* turnover
* SMA50
* SMA100
* SMA200
* diff_from_200
* CAR signal

Requirements:

* Save outputs:

  * CSV
  * Excel
  * JSON
* Sort by turnover descending
* Add timestamps
* Add logging

---

# PHASE 7 — GOOGLE SHEETS INTEGRATION

## Goal

Automatically publish results to Google Sheets.

---

# CODEX PROMPT — PHASE 7

Build Google Sheets integration for the screener.

Requirements:

* Use Google Sheets API
* Use service account credentials
* Upload dataframe to Google Sheets
* Clear old rows before upload
* Auto-format headers
* Add update timestamp
* Handle API failures gracefully

Libraries:

* gspread
* google-auth

Use environment variables for secrets.

---

# PHASE 8 — AUTOMATION

## Goal

Run automatically daily.

---

# CODEX PROMPT — PHASE 8

Create GitHub Actions automation for the screener.

Requirements:

* Daily scheduled workflow
* Manual trigger support
* Install dependencies
* Run screener automatically
* Upload logs as artifacts
* Retry on failure
* Use GitHub Secrets for credentials

Create:

* workflow YAML
* setup instructions

---

# PHASE 9 — DEBUGGING & RELIABILITY

## Goal

Prevent NSE blocking and scraping failures.

---

# COMMON ISSUES

## NSE Returning 401/403/404

Cause:

* bot detection
* missing cookies
* no session
* too many requests

---

# CODEX PROMPT — PHASE 9

Improve reliability of NSE data ingestion.

Requirements:

* Use requests.Session()
* Hit NSE homepage before API calls
* Maintain cookies
* Add rotating headers
* Add exponential backoff
* Add random delays
* Add caching layer
* Add retry decorators
* Detect failed downloads
* Fallback to cached data if NSE fails

Implement:

* centralized request manager
* structured logging
* anti-rate-limit protections

---

# PHASE 10 — OPTIONAL DASHBOARD

## Goal

Visual UI.

---

# CODEX PROMPT — PHASE 10

Build a Streamlit dashboard for the breakout screener.

Features:

* Top 250 stocks table
* Final breakout list
* Filters
* Search
* Bull/Bear visualization
* Last updated timestamp
* Export CSV button

Use:

* streamlit
* plotly

Keep UI clean and responsive.

---

# BEST PRACTICES

## NEVER

* tightly couple scraping + screener logic
* scrape HTML pages repeatedly
* request historical data repeatedly

## ALWAYS

* cache data
* use sessions
* use retries
* separate modules
* log errors
* use environment variables

---

# RECOMMENDED STACK

Backend:

* Python
* pandas
* numpy

Data:

* yfinance
* NSE bhavcopy

Indicators:

* pandas-ta

Storage:

* parquet
* sqlite

Automation:

* GitHub Actions

Visualization:

* Google Sheets
* Streamlit

---

# FINAL IMPLEMENTATION ORDER

1. Data pipeline
2. Historical storage
3. Indicator engine
4. Ranking engine
5. CAR engine
6. Final screener
7. Sheets integration
8. Automation
9. Dashboard

```

You can directly give this `plan.md` to your Codex workflow and execute phase-by-phase.
```
