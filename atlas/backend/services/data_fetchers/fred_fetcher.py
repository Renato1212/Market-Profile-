"""
FRED (Federal Reserve Economic Data) fetcher.
Free with API key. Macro context: yields, VIX, spreads, dollar, financial stress.
"""
import httpx
import pandas as pd
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

FRED_SERIES = {
    "vix": "VIXCLS",
    "yield_10y": "DGS10",
    "yield_2y": "DGS2",
    "yield_spread_10y2y": "T10Y2Y",
    "fed_funds": "DFF",
    "real_yield_10y": "DFII10",
    "trade_weighted_dollar": "DTWEXBGS",
    "financial_stress": "STLFSI4",
    "initial_claims": "ICSA",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
}


async def fetch_fred_series(series_id: str, api_key: str, observation_start: str = "2010-01-01") -> Optional[pd.DataFrame]:
    """Fetch a single FRED series."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
        "sort_order": "desc",
        "limit": 1000,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(FRED_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    return None

                df = pd.DataFrame(observations)
                df = df[df["value"] != "."]  # FRED uses "." for missing
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["value"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                df.attrs["series_id"] = series_id
                return df

            except Exception as e:
                logger.error(f"FRED fetch error {series_id} attempt {attempt+1}: {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return None


async def fetch_all_macro(api_key: str) -> Dict[str, dict]:
    """Fetch latest values for all key macro series."""
    import asyncio
    results = {}

    async def fetch_one(name: str, sid: str):
        df = await fetch_fred_series(sid, api_key, observation_start=(
            datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else None
            results[name] = {
                "value": round(float(latest["value"]), 4),
                "date": str(latest["date"].date()),
                "prior_value": round(float(prev["value"]), 4) if prev is not None else None,
                "change": round(float(latest["value"] - prev["value"]), 4) if prev is not None else 0,
            }

    tasks = [fetch_one(name, sid) for name, sid in FRED_SERIES.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Compute derived metrics
    if "yield_10y" in results and "yield_2y" in results:
        y10 = results["yield_10y"]["value"]
        y2 = results["yield_2y"]["value"]
        results["yield_curve"] = {
            "spread": round(y10 - y2, 3),
            "inverted": y10 < y2,
            "10y": y10,
            "2y": y2,
        }

    return results


async def fetch_yield_history(api_key: str, days: int = 252) -> dict:
    """Fetch 10Y and 2Y yield history for trend context."""
    start = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")

    y10_df = await fetch_fred_series("DGS10", api_key, observation_start=start)
    y2_df = await fetch_fred_series("DGS2", api_key, observation_start=start)

    result = {}
    if y10_df is not None:
        result["yield_10y"] = y10_df.tail(days)[["date", "value"]].to_dict("records")
    if y2_df is not None:
        result["yield_2y"] = y2_df.tail(days)[["date", "value"]].to_dict("records")

    return result
