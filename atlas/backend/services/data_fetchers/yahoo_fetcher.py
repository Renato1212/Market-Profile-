"""
Yahoo Finance data fetcher — primary market data source.
Supports daily OHLCV (10+ years) and 5-min intraday (60 days).
No API key required.
"""
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import pytz
import logging

logger = logging.getLogger(__name__)

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
ET = pytz.timezone("America/New_York")

SYMBOLS = {
    "ES": "ES=F",
    "NQ": "NQ=F",
    "YM": "YM=F",
    "RTY": "RTY=F",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "IWM": "IWM",
    "VIX": "^VIX",
    "VIX9D": "^VIX9D",
    "VIX3M": "^VIX3M",
    "VVIX": "^VVIX",
    "SPX": "^GSPC",
    "DXY": "DX-Y.NYB",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ATLAS/1.0; trading research)",
    "Accept": "application/json",
}


async def fetch_yahoo(symbol: str, interval: str = "1d", range_: str = "10y") -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Yahoo Finance v8 API with retry logic."""
    url = f"{YAHOO_BASE}/{symbol}"
    params = {"interval": interval, "range": range_, "includePrePost": "false"}

    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return _parse_yahoo_response(data, symbol, interval)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"Yahoo HTTP error for {symbol}: {e}")
                return None
            except Exception as e:
                logger.error(f"Yahoo fetch error for {symbol} attempt {attempt+1}: {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return None


def _parse_yahoo_response(data: dict, symbol: str, interval: str) -> Optional[pd.DataFrame]:
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]

        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        })

        # Convert timestamps
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df["datetime_et"] = df["datetime"].dt.tz_convert(ET)

        # Drop rows with NaN OHLC
        df = df.dropna(subset=["open", "high", "low", "close"])

        # For daily data, create date column
        if interval == "1d":
            df["date"] = df["datetime_et"].dt.date.astype(str)
        else:
            df["date"] = df["datetime_et"].dt.strftime("%Y-%m-%d")
            df["time_et"] = df["datetime_et"].dt.strftime("%H:%M")

        df = df.sort_values("datetime").reset_index(drop=True)
        df.attrs["symbol"] = symbol
        return df

    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Yahoo parse error for {symbol}: {e}")
        return None


async def fetch_es_daily(years: int = 12) -> Optional[pd.DataFrame]:
    """Fetch ES=F daily bars, extended history."""
    range_map = {1: "1y", 2: "2y", 5: "5y", 10: "10y", 12: "max"}
    range_str = range_map.get(years, "max")
    return await fetch_yahoo("ES=F", interval="1d", range_=range_str)


async def fetch_es_intraday_5min(days: int = 60) -> Optional[pd.DataFrame]:
    """Fetch ES=F 5-minute intraday bars (last N days, max 60 from Yahoo)."""
    days = min(days, 60)
    range_str = f"{days}d"
    df = await fetch_yahoo("ES=F", interval="5m", range_=range_str)
    if df is None:
        return None

    # Filter to cash session only: 09:30–16:00 ET
    df["hour"] = df["datetime_et"].dt.hour
    df["minute"] = df["datetime_et"].dt.minute
    df["time_decimal"] = df["hour"] + df["minute"] / 60

    cash = df[(df["time_decimal"] >= 9.5) & (df["time_decimal"] < 16.0)].copy()
    cash["bar_index"] = cash.groupby("date").cumcount()
    return cash.reset_index(drop=True)


async def fetch_spy_options_chain() -> Optional[dict]:
    """Fetch SPY options chain using Yahoo Finance options endpoint."""
    url = "https://query1.finance.yahoo.com/v7/finance/options/SPY"
    chains = {}

    async with httpx.AsyncClient(timeout=45.0, headers=HEADERS) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            option_chain = data.get("optionChain", {}).get("result", [])
            if not option_chain:
                return None

            result = option_chain[0]
            expirations = result.get("expirationDates", [])
            quote = result.get("quote", {})
            spy_price = quote.get("regularMarketPrice", 0)

            # Fetch nearest 4 expirations
            for exp_ts in expirations[:4]:
                exp_url = f"{url}?date={exp_ts}"
                exp_resp = await client.get(exp_url)
                exp_resp.raise_for_status()
                exp_data = exp_resp.json()
                exp_result = exp_data["optionChain"]["result"][0]
                options = exp_result.get("options", [{}])[0]

                exp_date = datetime.fromtimestamp(exp_ts).strftime("%Y-%m-%d")
                chains[exp_date] = {
                    "calls": options.get("calls", []),
                    "puts": options.get("puts", []),
                    "expiration_ts": exp_ts,
                }

            return {"spy_price": spy_price, "chains": chains, "fetched_at": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error(f"SPY options chain error: {e}")
            return None


async def fetch_vix_term_structure() -> dict:
    """Fetch VIX, VIX9D, VIX3M, VVIX for term structure analysis."""
    results = {}
    symbols = {"vix": "^VIX", "vix9d": "^VIX9D", "vix3m": "^VIX3M", "vvix": "^VVIX"}

    for name, sym in symbols.items():
        df = await fetch_yahoo(sym, interval="1d", range_="5d")
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            results[name] = {
                "current": round(float(last["close"]), 2),
                "prior_close": round(float(df.iloc[-2]["close"]), 2) if len(df) > 1 else None,
                "change": round(float(last["close"] - df.iloc[-2]["close"]), 2) if len(df) > 1 else 0,
                "change_pct": round(float((last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100), 2) if len(df) > 1 else 0,
            }

    # Compute term structure signals
    if "vix9d" in results and "vix" in results and "vix3m" in results:
        v9 = results["vix9d"]["current"]
        v = results["vix"]["current"]
        v3m = results["vix3m"]["current"]
        results["term_structure"] = {
            "vix9d_vix_ratio": round(v9 / v, 3) if v > 0 else None,
            "vix_vix3m_ratio": round(v / v3m, 3) if v3m > 0 else None,
            "contango": v9 < v < v3m,
            "backwardation": v9 > v or v > v3m,
            "stress_flag": v9 > v3m,
        }

    return results


async def fetch_crypto_overnight() -> dict:
    """Fetch BTC/ETH overnight change as risk-on/off proxy."""
    results = {}
    symbols = {"btc": "BTC-USD", "eth": "ETH-USD"}

    for name, sym in symbols.items():
        df = await fetch_yahoo(sym, interval="1h", range_="2d")
        if df is not None and len(df) >= 2:
            # Overnight window: 16:00 ET yesterday → 09:30 ET today
            now_et = datetime.now(ET)
            yesterday_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0) - timedelta(days=1)
            today_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

            overnight_bars = df[
                (df["datetime_et"] >= yesterday_close) &
                (df["datetime_et"] <= today_open)
            ]

            if len(overnight_bars) >= 2:
                on_open = float(overnight_bars.iloc[0]["open"])
                on_last = float(overnight_bars.iloc[-1]["close"])
                on_high = float(overnight_bars["high"].max())
                on_low = float(overnight_bars["low"].min())
                results[name] = {
                    "overnight_open": on_open,
                    "overnight_last": on_last,
                    "overnight_high": on_high,
                    "overnight_low": on_low,
                    "change_pct": round((on_last - on_open) / on_open * 100, 2) if on_open > 0 else 0,
                    "risk_signal": "risk_on" if on_last > on_open else "risk_off",
                }

    return results


async def fetch_dxy_overnight() -> dict:
    """Fetch DXY Dollar Index data."""
    df = await fetch_yahoo("DX-Y.NYB", interval="1h", range_="2d")
    if df is not None and len(df) >= 2:
        last = float(df.iloc[-1]["close"])
        prev = float(df.iloc[-2]["close"])
        return {
            "current": round(last, 3),
            "change": round(last - prev, 3),
            "change_pct": round((last - prev) / prev * 100, 3) if prev > 0 else 0,
        }
    return {}


async def get_es_spy_multiplier() -> float:
    """Compute live ES/SPY multiplier for GEX conversion. Never hardcode 10."""
    es_df = await fetch_yahoo("ES=F", interval="1m", range_="1d")
    spy_df = await fetch_yahoo("SPY", interval="1m", range_="1d")

    if es_df is not None and spy_df is not None and len(es_df) > 0 and len(spy_df) > 0:
        es_price = float(es_df.iloc[-1]["close"])
        spy_price = float(spy_df.iloc[-1]["close"])
        if spy_price > 0:
            return es_price / spy_price

    return 10.0  # fallback only
