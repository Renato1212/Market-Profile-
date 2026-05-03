"""
CFTC Commitments of Traders (COT) fetcher.
Free public API, no key required.
Tracks smart money (commercial) vs speculative positioning in ES, NQ, ZB, ZN.
"""
import httpx
import pandas as pd
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

CFTC_API_BASE = "https://publicreporting.cftc.gov/resource"

# CFTC dataset IDs for futures-only COT legacy report
# ES (S&P 500 E-Mini) = market code 13874+
CFTC_DATASETS = {
    "es_cot": "6dca-aqww",   # Disaggregated COT
    "legacy_cot": "jun7-fc8e", # Legacy COT
}

# Market names in CFTC data
ES_MARKET_NAME = "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE"
NQ_MARKET_NAME = "E-MINI NASDAQ-100 - CHICAGO MERCANTILE EXCHANGE"


async def fetch_cot_data(dataset: str = "jun7-fc8e", market_name: str = ES_MARKET_NAME, limit: int = 52) -> Optional[pd.DataFrame]:
    """
    Fetch COT data for a specific futures market.
    Returns last N weeks of positioning data.
    """
    url = f"{CFTC_API_BASE}/{dataset}.json"
    params = {
        "$where": f"market_and_exchange_names='{market_name}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return None

                df = pd.DataFrame(data)
                if "report_date_as_yyyy_mm_dd" in df.columns:
                    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
                    df = df.sort_values("date").reset_index(drop=True)

                return df

            except Exception as e:
                logger.error(f"CFTC fetch error attempt {attempt+1}: {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return None


async def get_es_cot_analysis() -> dict:
    """Parse ES COT data into smart money positioning signals."""
    df = await fetch_cot_data(limit=26)
    if df is None or df.empty:
        return {"error": "COT data unavailable", "data": []}

    # Key columns in legacy COT
    numeric_cols = [
        "noncomm_positions_long_all", "noncomm_positions_short_all",
        "comm_positions_long_all", "comm_positions_short_all",
        "nonrept_positions_long_all", "nonrept_positions_short_all",
        "open_interest_all",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    result = []
    for _, row in df.iterrows():
        try:
            nc_long = float(row.get("noncomm_positions_long_all", 0) or 0)
            nc_short = float(row.get("noncomm_positions_short_all", 0) or 0)
            comm_long = float(row.get("comm_positions_long_all", 0) or 0)
            comm_short = float(row.get("comm_positions_short_all", 0) or 0)
            oi = float(row.get("open_interest_all", 1) or 1)

            nc_net = nc_long - nc_short
            comm_net = comm_long - comm_short
            nc_net_pct = (nc_net / oi * 100) if oi > 0 else 0

            result.append({
                "date": str(row.get("date", "")[:10] if "date" in row else ""),
                "large_spec_net": round(nc_net),
                "large_spec_net_pct_oi": round(nc_net_pct, 2),
                "commercial_net": round(comm_net),
                "open_interest": round(oi),
            })
        except Exception:
            continue

    if not result:
        return {"error": "Parse failed", "data": []}

    latest = result[-1]
    prior = result[-2] if len(result) > 1 else latest

    # Net spec positioning signal
    spec_net = latest["large_spec_net"]
    spec_change = spec_net - prior["large_spec_net"]

    # Percentile over available history
    nets = [r["large_spec_net"] for r in result]
    pct = sum(1 for n in nets if n <= spec_net) / len(nets) * 100

    if spec_net > 0 and spec_change > 0:
        signal = "large_specs_adding_longs"
        bias = "bullish"
    elif spec_net > 0 and spec_change < 0:
        signal = "large_specs_reducing_longs"
        bias = "neutral"
    elif spec_net < 0 and spec_change < 0:
        signal = "large_specs_adding_shorts"
        bias = "bearish"
    else:
        signal = "large_specs_reducing_shorts"
        bias = "neutral"

    return {
        "latest_date": latest["date"],
        "large_spec_net": latest["large_spec_net"],
        "large_spec_net_pct_oi": latest["large_spec_net_pct_oi"],
        "weekly_change": round(spec_change),
        "percentile_52w": round(pct, 1),
        "signal": signal,
        "bias": bias,
        "history": result[-12:],  # Last 12 weeks for chart
    }
