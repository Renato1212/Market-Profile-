"""Gap Fill API routes."""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db

router = APIRouter()


@router.get("/tables")
async def get_gap_tables(
    years: int = Query(10, ge=1, le=15),
    db: AsyncSession = Depends(get_db)
):
    """Get all gap fill statistical tables (A, B, C)."""
    from services.gap_engine.gap_statistics import (
        build_table_a_opening_location, build_table_b_gap_size,
        build_table_c_cumulative_curve
    )
    from services.data_fetchers.cache_layer import get_cached, set_cached

    cache_key = f"gap_tables_{years}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    gap_df = await _load_gap_df(db, years)
    if gap_df is None or len(gap_df) == 0:
        raise HTTPException(status_code=503, detail="Gap data not yet computed. Run data refresh.")

    result = {
        "table_a": build_table_a_opening_location(gap_df),
        "table_b": build_table_b_gap_size(gap_df),
        "table_c": build_table_c_cumulative_curve(gap_df),
        "total_sessions": len(gap_df),
        "date_range": {
            "start": str(gap_df["date"].min()),
            "end": str(gap_df["date"].max()),
        },
    }

    await set_cached(cache_key, result, ttl_seconds=86400)
    return result


@router.get("/calculator")
async def gap_fill_calculator(
    direction: str = Query(..., regex="^(up|down)$"),
    size_pts: float = Query(..., gt=0),
    day_of_week: Optional[int] = Query(None, ge=0, le=4),
    vix: Optional[float] = Query(None),
    regime: Optional[str] = Query(None),
    prior_day_type: Optional[str] = Query(None),
    is_fomc: bool = Query(False),
    gap_context: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Interactive gap fill probability calculator."""
    from services.gap_engine.gap_statistics import compute_fill_probability
    from services.data_fetchers.cache_layer import get_cached, set_cached
    import hashlib
    import json

    params = dict(direction=direction, size_pts=size_pts, day_of_week=day_of_week,
                  vix=vix, regime=regime, prior_day_type=prior_day_type,
                  is_fomc=is_fomc, gap_context=gap_context)
    cache_key = "gap_calc_" + hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]

    cached = await get_cached(cache_key)
    if cached:
        return cached

    gap_df = await _load_gap_df(db, 10)
    if gap_df is None:
        raise HTTPException(status_code=503, detail="Gap data unavailable")

    result = compute_fill_probability(
        gap_df=gap_df,
        gap_direction=direction,
        gap_size_pts=size_pts,
        day_of_week=day_of_week,
        vix_level=vix,
        trend_regime=regime,
        prior_day_type=prior_day_type,
        is_fomc=is_fomc,
        gap_context=gap_context,
    )

    await set_cached(cache_key, result, ttl_seconds=3600)
    return result


@router.get("/hypothesis-tests")
async def hypothesis_tests(db: AsyncSession = Depends(get_db)):
    """Run all hypothesis tests and return verdicts."""
    from services.gap_engine.gap_statistics import run_hypothesis_tests
    from services.data_fetchers.cache_layer import get_cached, set_cached

    cached = await get_cached("hypothesis_tests")
    if cached:
        return cached

    gap_df = await _load_gap_df(db, 10)
    if gap_df is None:
        raise HTTPException(status_code=503, detail="Gap data unavailable")

    result = {"tests": run_hypothesis_tests(gap_df)}
    await set_cached("hypothesis_tests", result, ttl_seconds=86400)
    return result


@router.get("/today")
async def today_gap_status():
    """Get today's gap status with real-time computation."""
    from services.data_fetchers.yahoo_fetcher import fetch_es_daily
    from services.gap_engine.gap_calculator import compute_gap_stats_for_session
    from services.data_fetchers.calendar_fetcher import get_calendar_flags
    from datetime import date

    daily = await fetch_es_daily(years=2)
    if daily is None or len(daily) < 2:
        raise HTTPException(status_code=503, detail="Price data unavailable")

    today = daily.iloc[-1]
    prior = daily.iloc[-2]

    gap_stats = compute_gap_stats_for_session(today, prior)
    cal = get_calendar_flags(date.today())

    return {
        "date": str(today["date"]),
        "current_price": round(float(today["close"]), 2),
        "open": round(float(today["open"]), 2),
        "prior_close": round(float(prior["close"]), 2),
        "gap": gap_stats,
        "calendar": cal,
    }


async def _load_gap_df(db: AsyncSession, years: int):
    """Load gap DataFrame from DB, filtered by years."""
    from sqlalchemy import select, text
    from models.database import DailySession
    from datetime import datetime, timedelta
    import pandas as pd

    cutoff = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    result = await db.execute(
        select(DailySession).where(
            DailySession.date >= cutoff,
            DailySession.excluded == False,
            DailySession.gap_direction != None,
        ).order_by(DailySession.date)
    )
    rows = result.scalars().all()

    if not rows:
        return None

    data = []
    for row in rows:
        data.append({c.key: getattr(row, c.key) for c in row.__table__.columns})

    return pd.DataFrame(data)
