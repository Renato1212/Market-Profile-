"""A Period auction analytics routes."""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db
from datetime import datetime
import pytz

ET = pytz.timezone("America/New_York")
router = APIRouter()


@router.get("/live")
async def get_live_a_period():
    """
    Get live A Period tracker data.
    Returns current bars, type classification, and day type probabilities.
    """
    from services.data_fetchers.yahoo_fetcher import fetch_es_intraday_5min, fetch_es_daily
    from services.aperiod_engine.aperiod_classifier import classify_a_period_type, predict_day_type_live
    from services.gap_engine.gap_calculator import classify_gap_context
    import asyncio

    now_et = datetime.now(ET)
    today_str = now_et.strftime("%Y-%m-%d")

    # Fetch current day 5-min bars
    intraday = await fetch_es_intraday_5min(days=5)
    daily = await fetch_es_daily(years=2)

    if intraday is None or daily is None:
        raise HTTPException(status_code=503, detail="Market data unavailable")

    today_bars = intraday[intraday["date"] == today_str].sort_values("bar_index")
    a_bars = today_bars[today_bars["bar_index"] < 6]  # First 6 bars = A Period

    # Prior session
    today_daily = daily[daily["date"] == today_str]
    prior_idx = daily[daily["date"] < today_str].index.max()
    prior_row = daily.loc[prior_idx] if prior_idx is not None else None

    prior_close = float(prior_row["close"]) if prior_row is not None else None
    pdh = float(prior_row["high"]) if prior_row is not None else None
    pdl = float(prior_row["low"]) if prior_row is not None else None

    # Compute 20-day average range
    recent_daily = daily.tail(22).iloc[:-1]  # Last 20 sessions (exclude today)
    avg_range_20d = float((recent_daily["high"] - recent_daily["low"]).mean()) if len(recent_daily) >= 5 else None

    a_period_live = {}
    if len(a_bars) > 0:
        a_period_live = classify_a_period_type(
            a_bars, prior_close=prior_close, pdh=pdh, pdl=pdl,
            avg_range_20d=avg_range_20d
        )

    # Day type prediction
    open_location = "unknown"
    if prior_close and len(a_bars) > 0:
        open_price = float(a_bars.iloc[0]["open"])
        open_location = classify_gap_context(open_price, None, None, None, pdh, pdl)

    day_type_pred = predict_day_type_live(
        a_bars, open_location=open_location,
    ) if len(a_bars) > 0 else {}

    # Session time context
    market_open = ET.localize(now_et.replace(hour=9, minute=30, second=0, microsecond=0))
    a_period_end = ET.localize(now_et.replace(hour=10, minute=0, second=0, microsecond=0))
    in_a_period = market_open <= now_et < a_period_end
    a_complete = now_et >= a_period_end

    return {
        "date": today_str,
        "current_time_et": now_et.strftime("%H:%M:%S"),
        "in_a_period": in_a_period,
        "a_period_complete": a_complete,
        "bars_count": len(a_bars),
        "a_period": a_period_live,
        "day_type_prediction": day_type_pred,
        "prior_close": prior_close,
        "pdh": pdh,
        "pdl": pdl,
        "bars": today_bars[["bar_index", "open", "high", "low", "close", "volume", "time_et"]].to_dict("records") if len(today_bars) > 0 else [],
    }


@router.get("/history")
async def get_a_period_history(
    years: int = Query(5, ge=1, le=12),
    a_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get historical A Period data with statistics."""
    from services.data_fetchers.cache_layer import get_cached, set_cached
    from sqlalchemy import select
    from models.database import DailySession
    from datetime import timedelta
    import pandas as pd

    cache_key = f"aperiod_history_{years}_{a_type}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    cutoff = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    query = select(DailySession).where(
        DailySession.date >= cutoff,
        DailySession.excluded == False,
        DailySession.a_type != None,
    ).order_by(DailySession.date)

    if a_type:
        query = query.where(DailySession.a_type == a_type)

    result = await db.execute(query)
    rows = result.scalars().all()

    if not rows:
        return {"sessions": [], "stats": {}}

    data = [{"date": r.date, "a_type": r.a_type, "a_range": r.a_range,
             "a_close_position": r.a_close_position, "a_direction": r.a_direction,
             "day_type": r.day_type, "a_high_held_eod": r.a_high_held_eod,
             "a_low_held_eod": r.a_low_held_eod, "a_extension_direction": r.a_extension_direction,
             "filled_same_session": r.filled_same_session} for r in rows]

    df = pd.DataFrame(data)

    # Compute type distribution stats
    type_stats = {}
    for typ in df["a_type"].unique():
        t_df = df[df["a_type"] == typ]
        type_stats[typ] = {
            "count": len(t_df),
            "pct_of_total": round(len(t_df) / len(df) * 100, 1),
            "trend_day_rate": round(t_df["day_type"].str.contains("trend", na=False).mean() * 100, 1),
            "avg_a_close_position": round(t_df["a_close_position"].mean(), 1),
            "a_high_held_rate": round(t_df["a_high_held_eod"].mean() * 100, 1) if t_df["a_high_held_eod"].notna().any() else None,
        }

    result = {
        "sessions": data[-100:],  # Last 100 sessions
        "stats": type_stats,
        "total_sessions": len(df),
    }

    await set_cached(cache_key, result, ttl_seconds=86400)
    return result


async def get_cached(key):
    from services.data_fetchers.cache_layer import get_cached as gc
    return await gc(key)


async def set_cached(key, val, ttl_seconds):
    from services.data_fetchers.cache_layer import set_cached as sc
    await sc(key, val, ttl_seconds)
