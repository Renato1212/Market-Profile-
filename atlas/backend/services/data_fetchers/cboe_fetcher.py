"""
CBOE public data fetcher — free, no API key required.
Put/Call ratios, VIX history, SPX options data.
"""
import httpx
import pandas as pd
import io
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CBOE_PC_TOTAL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpcarchive.csv"
CBOE_PC_EQUITY = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypcarchive.csv"
CBOE_PC_INDEX = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/indexpcarchive.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ATLAS/1.0; trading research)",
    "Referer": "https://www.cboe.com/",
}


async def fetch_cboe_pc_ratio(source: str = "total") -> Optional[pd.DataFrame]:
    """
    Fetch CBOE Put/Call ratio CSV.
    source: 'total', 'equity', or 'index'
    Returns DataFrame with columns: date, put_volume, call_volume, total_pc_ratio
    """
    url_map = {
        "total": CBOE_PC_TOTAL,
        "equity": CBOE_PC_EQUITY,
        "index": CBOE_PC_INDEX,
    }
    url = url_map.get(source, CBOE_PC_TOTAL)

    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                df = pd.read_csv(io.StringIO(resp.text))
                df.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]

                # Normalize column names across CBOE CSV variants
                col_map = {}
                for col in df.columns:
                    if "date" in col:
                        col_map[col] = "date"
                    elif "put" in col and "vol" in col:
                        col_map[col] = "put_volume"
                    elif "call" in col and "vol" in col:
                        col_map[col] = "call_volume"
                    elif "total" in col or "ratio" in col or "p_c" in col or "pc" in col:
                        col_map[col] = "total_pc_ratio"
                df = df.rename(columns=col_map)

                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["date"])
                    df = df.sort_values("date").reset_index(drop=True)

                if "total_pc_ratio" not in df.columns and "put_volume" in df.columns and "call_volume" in df.columns:
                    df["total_pc_ratio"] = df["put_volume"] / df["call_volume"].replace(0, float("nan"))

                df.attrs["source"] = source
                return df

            except Exception as e:
                logger.error(f"CBOE P/C fetch error attempt {attempt+1}: {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return None


async def get_pc_ratio_analysis() -> dict:
    """Compute P/C ratio analysis with signals."""
    df = await fetch_cboe_pc_ratio("total")
    if df is None or "total_pc_ratio" not in df.columns:
        return {}

    df = df.dropna(subset=["total_pc_ratio"])
    if len(df) < 10:
        return {}

    latest = float(df.iloc[-1]["total_pc_ratio"])
    ma10 = float(df["total_pc_ratio"].tail(10).mean())
    ma21 = float(df["total_pc_ratio"].tail(21).mean())
    pct_1y = float(df["total_pc_ratio"].tail(252).rank(pct=True).iloc[-1]) * 100

    # Signal interpretation
    if latest > 1.15:
        signal = "extreme_fear"
        interpretation = "Bearish capitulation — contrarian bullish"
    elif latest > 0.95:
        signal = "fear"
        interpretation = "Elevated put buying — mild bearish bias"
    elif latest < 0.65:
        signal = "extreme_complacency"
        interpretation = "Excessive call buying — contrarian bearish"
    elif latest < 0.75:
        signal = "complacency"
        interpretation = "Low hedging demand — mild bearish bias"
    else:
        signal = "neutral"
        interpretation = "Balanced options sentiment"

    return {
        "latest": round(latest, 3),
        "ma10": round(ma10, 3),
        "ma21": round(ma21, 3),
        "percentile_1y": round(pct_1y, 1),
        "signal": signal,
        "interpretation": interpretation,
        "extremes": {
            "bearish_threshold": 1.1,
            "bullish_threshold": 0.7,
        },
        "history": df.tail(30)[["date", "total_pc_ratio"]].to_dict("records"),
    }
