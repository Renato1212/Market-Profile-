"""Market data API routes — live prices, macro, COT."""
from fastapi import APIRouter, HTTPException, Query
from services.data_fetchers.cache_layer import get_cached, set_cached

router = APIRouter()


@router.get("/snapshot")
async def get_market_snapshot():
    """Full market snapshot: ES price, VIX, yields, DXY, crypto, GEX regime."""
    import asyncio
    from services.data_fetchers.yahoo_fetcher import (
        fetch_vix_term_structure, fetch_crypto_overnight, fetch_dxy_overnight, fetch_yahoo
    )
    from datetime import datetime

    cached = await get_cached("market_snapshot")
    if cached:
        return cached

    tasks = await asyncio.gather(
        fetch_yahoo("ES=F", interval="1m", range_="1d"),
        fetch_vix_term_structure(),
        fetch_crypto_overnight(),
        fetch_dxy_overnight(),
        get_cached("gex_dashboard"),
        return_exceptions=True,
    )
    es_bars, vix, crypto, dxy, gex = [t if not isinstance(t, Exception) else None for t in tasks]

    es_price = es_change = es_change_pct = None
    if es_bars is not None and len(es_bars) >= 2:
        es_price = round(float(es_bars.iloc[-1]["close"]), 2)
        es_prev = round(float(es_bars.iloc[0]["open"]), 2)
        es_change = round(es_price - es_prev, 2)
        es_change_pct = round(es_change / es_prev * 100, 3) if es_prev else 0

    result = {
        "es": {"price": es_price, "change": es_change, "change_pct": es_change_pct or 0},
        "vix": vix or {},
        "crypto": crypto or {},
        "dxy": dxy or {},
        "gex_regime": (gex or {}).get("regime"),
        "gex_net": (gex or {}).get("net_gex"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    await set_cached("market_snapshot", result, ttl_seconds=60)
    return result


@router.get("/macro")
async def get_macro_data():
    """Get all FRED macro data."""
    from services.data_fetchers.fred_fetcher import fetch_all_macro
    from config import settings

    cached = await get_cached("macro_data")
    if cached:
        return cached

    if not settings.fred_api_key:
        return {"error": "FRED API key not configured", "data": {}}

    result = await fetch_all_macro(settings.fred_api_key)
    await set_cached("macro_data", result, ttl_seconds=300)
    return result


@router.get("/cot")
async def get_cot_data():
    """Get CFTC COT positioning data for ES."""
    from services.data_fetchers.cftc_fetcher import get_es_cot_analysis

    cached = await get_cached("cot_data")
    if cached:
        return cached

    result = await get_es_cot_analysis()
    await set_cached("cot_data", result, ttl_seconds=604800)
    return result


@router.get("/ohlcv/daily")
async def get_daily_ohlcv(symbol: str = "ES=F", years: int = Query(5, ge=1, le=12)):
    """Get daily OHLCV history."""
    from services.data_fetchers.yahoo_fetcher import fetch_yahoo

    cache_key = f"daily_ohlcv_{symbol}_{years}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    range_map = {1: "1y", 2: "2y", 5: "5y", 10: "10y", 12: "max"}
    df = await fetch_yahoo(symbol, interval="1d", range_=range_map.get(years, "5y"))

    if df is None:
        raise HTTPException(status_code=503, detail=f"Price data unavailable for {symbol}")

    result = {
        "symbol": symbol,
        "data": df[["date", "open", "high", "low", "close", "volume"]].tail(years * 252).to_dict("records"),
        "count": len(df),
    }

    await set_cached(cache_key, result, ttl_seconds=86400)
    return result
