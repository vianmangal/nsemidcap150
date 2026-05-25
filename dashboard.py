from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")


def _latest_file(pattern: str) -> Path | None:
    matches = list(OUTPUT_DIR.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


@st.cache_data(ttl=300)
def load_csv(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=300)
def load_indicator_latest() -> pd.DataFrame:
    indicators_dir = DATA_DIR / "processed" / "indicators"
    if not indicators_dir.exists():
        return pd.DataFrame()
    frames: list[pd.DataFrame] = []
    for path in indicators_dir.glob("*.parquet"):
        df = pd.read_parquet(path)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.sort_values("date").tail(1)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def filter_by_search(df: pd.DataFrame, search: str, symbol_col: str = "symbol") -> pd.DataFrame:
    if df.empty or not search:
        return df
    if symbol_col not in df.columns:
        return df
    mask = df[symbol_col].astype(str).str.contains(search, case=False, na=False)
    return df[mask]


def main() -> None:
    st.set_page_config(page_title="NSE Breakout Screener", layout="wide")

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Space+Grotesk:wght@400;600;700&display=swap');
        :root {
            --ink: #0f172a;
            --muted: #475569;
            --accent: #ff6b35;
            --accent-2: #0ea5e9;
            --card: #ffffff;
            --border: #e5e7eb;
        }
        html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
        h1, h2, h3, h4 { font-family: 'Fraunces', serif; letter-spacing: -0.3px; }
        .stApp {
            background:
                radial-gradient(circle at top left, #f5efe2 0%, #f7f9ff 40%, #e9f7f3 100%),
                linear-gradient(140deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.2) 100%);
        }
        .block-container { padding-top: 2rem; }
        .hero {
            background: linear-gradient(120deg, #111827 0%, #1f2937 60%, #0f172a 100%);
            color: #f8fafc;
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
            position: relative;
            overflow: hidden;
        }
        .hero:after {
            content: "";
            position: absolute;
            top: -40px;
            right: -60px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(255,107,53,0.5) 0%, rgba(255,107,53,0) 70%);
            filter: blur(6px);
        }
        .pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255,255,255,0.2);
            font-size: 0.8rem;
            margin-right: 6px;
        }
        .kpi-card {
            background: var(--card);
            border: 1px solid var(--border);
            padding: 1rem 1.1rem;
            border-radius: 14px;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .kpi-label { color: var(--muted); font-size: 0.85rem; }
        .kpi-value { font-size: 1.4rem; font-weight: 700; }
        .table-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.6rem; }
        .fade-in { animation: fadeIn 0.8s ease-in-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("NSE Breakout Screener")
    st.caption("Phase 10 dashboard — live insights from latest outputs.")

    top_250_path = _latest_file("top_250_turnover_*.csv")
    final_path = _latest_file("final_screener_daily_*.csv")
    relaxed_path = _latest_file("final_screener_relaxed_*.csv")

    top_250_df = load_csv(top_250_path)
    final_df = load_csv(final_path)
    relaxed_df = load_csv(relaxed_path)
    indicators_latest = load_indicator_latest()

    last_updated: str | None = None
    latest_paths = [p for p in [top_250_path, final_path, relaxed_path] if p is not None]
    if latest_paths:
        latest_time = max(p.stat().st_mtime for p in latest_paths)
        last_updated = datetime.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M")

    with st.sidebar:
        st.header("Filters")
        search = st.text_input("Search symbol", "")
        min_turnover = st.number_input("Min turnover", min_value=0.0, value=0.0, step=1_000_000.0)
        diff_range = st.slider("Diff from 200 DMA", min_value=-50.0, max_value=50.0, value=(-10.0, 10.0))
        car_options = ["BUY_AVERAGE_OUT", "AVOID_HOLD"]
        car_selected = st.multiselect("CAR signal", options=car_options, default=car_options)
        if last_updated:
            st.caption(f"Last updated: {last_updated}")

    top5_main = pd.DataFrame()
    if not top_250_df.empty and "turnover" in top_250_df.columns:
        top5_main = top_250_df.sort_values("turnover", ascending=False).head(5)

    hero_cols = st.columns([1.6, 1])
    with hero_cols[0]:
        st.markdown(
            f"""
            <div class="hero fade-in">
                <div class="pill">Daily momentum</div>
                <div class="pill">Automated signals</div>
                <h2 style="margin: 0.4rem 0 0.2rem 0;">Market Pulse</h2>
                <p style="margin: 0; color: #d1d5db;">Snapshot of turnover leaders and breakout candidates.</p>
                <p style="margin: 0.75rem 0 0 0; font-size: 0.85rem; color: #cbd5f5;">Last updated: {last_updated or "—"}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_cols[1]:
        st.markdown("<div class='table-card fade-in'><div class='section-title'>Top 5 Leaders</div></div>", unsafe_allow_html=True)
        if top5_main.empty:
            st.info("Top 250 data not available.")
        else:
            st.dataframe(top5_main, use_container_width=True, height=240)

    bull_count = int((indicators_latest.get("trend") == "Bull Run").sum()) if not indicators_latest.empty else 0
    bear_count = int((indicators_latest.get("trend") == "Bear Run").sum()) if not indicators_latest.empty else 0

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Top 250 rows</div><div class='kpi-value'>{len(top_250_df)}</div></div>",
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Final rows</div><div class='kpi-value'>{len(final_df)}</div></div>",
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Relaxed rows</div><div class='kpi-value'>{len(relaxed_df)}</div></div>",
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Bull / Bear</div><div class='kpi-value'>{bull_count} / {bear_count}</div></div>",
            unsafe_allow_html=True,
        )

    tabs = st.tabs(["Final Screener", "Relaxed", "Top 250", "Bull/Bear"])

    with tabs[0]:
        st.subheader("Final Screener")
        df = final_df.copy()
        if "turnover" in df.columns:
            df = df[df["turnover"].fillna(0) >= min_turnover]
        if "diff_from_200" in df.columns:
            df = df[df["diff_from_200"].between(diff_range[0], diff_range[1], inclusive="both")]
        if "car_signal" in df.columns:
            df = df[df["car_signal"].isin(car_selected)]
        df = filter_by_search(df, search)
        if df.empty:
            st.warning("No rows match the filters.")
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name=final_path.name if final_path else "final_screener.csv",
                mime="text/csv",
            )

    with tabs[1]:
        st.subheader("Relaxed Screener")
        df = relaxed_df.copy()
        if "turnover" in df.columns:
            df = df[df["turnover"].fillna(0) >= min_turnover]
        if "diff_from_200" in df.columns:
            df = df[df["diff_from_200"].between(diff_range[0], diff_range[1], inclusive="both")]
        df = filter_by_search(df, search)
        if df.empty:
            st.warning("No relaxed rows found.")
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name=relaxed_path.name if relaxed_path else "final_screener_relaxed.csv",
                mime="text/csv",
            )

    with tabs[2]:
        st.subheader("Top 250 Turnover")
        df = top_250_df.copy()
        df = filter_by_search(df, search)
        if "turnover" in df.columns:
            df = df[df["turnover"].fillna(0) >= min_turnover]
            top5 = df.sort_values("turnover", ascending=False).head(5)
        else:
            top5 = pd.DataFrame()
        if df.empty:
            st.warning("Top 250 file not found or filtered out.")
        if not top5.empty:
            st.markdown("**Top 5 by turnover**")
            st.dataframe(top5, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    with tabs[3]:
        st.subheader("Bull/Bear Overview")
        if indicators_latest.empty or "trend" not in indicators_latest.columns:
            st.warning("Indicator data not available for Bull/Bear overview.")
        else:
            trend_counts = indicators_latest["trend"].fillna("Unknown").value_counts().reset_index()
            trend_counts.columns = ["trend", "count"]
            fig = px.bar(
                trend_counts,
                x="trend",
                y="count",
                color="trend",
                color_discrete_sequence=["#2563eb", "#ef4444", "#f59e0b", "#94a3b8"],
            )
            fig.update_layout(height=360, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
