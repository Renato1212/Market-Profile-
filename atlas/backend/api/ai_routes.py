"""AI Copilot API routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db
from config import settings
from datetime import datetime
import pytz

ET = pytz.timezone("America/New_York")
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []


@router.get("/briefing/today")
async def get_today_briefing(db: AsyncSession = Depends(get_db)):
    """
    Get or generate today's pre-market briefing.
    Cached once per day. Uses claude-opus-4-7.
    """
    from services.ai_copilot.copilot import generate_premarket_briefing
    from services.data_fetchers.cache_layer import get_cached, set_cached
    from models.database import AIBriefing
    from sqlalchemy import select

    today = datetime.now(ET).strftime("%Y-%m-%d")
    cache_key = f"ai_briefing_{today}"

    # Check memory cache first
    cached = await get_cached(cache_key)
    if cached:
        return cached

    # Check DB cache
    result = await db.execute(
        select(AIBriefing).where(AIBriefing.date == today).order_by(AIBriefing.id.desc())
    )
    existing = result.scalar_one_or_none()
    if existing:
        data = {"content": existing.content, "date": today, "cached": True, "model": existing.model_used}
        await set_cached(cache_key, data, ttl_seconds=86400)
        return data

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured (ANTHROPIC_API_KEY missing)")

    # Build context from all data sources
    context = await _build_full_context(today, db)

    result_ai = await generate_premarket_briefing(context, settings.anthropic_api_key)

    if result_ai.get("success"):
        # Store in DB
        briefing = AIBriefing(
            date=today,
            content=result_ai["content"],
            model_used=result_ai.get("model", ""),
            tokens_used=result_ai.get("tokens_used", 0),
        )
        db.add(briefing)
        await db.commit()

    response = {
        "content": result_ai.get("content", ""),
        "date": today,
        "cached": False,
        "model": result_ai.get("model", ""),
        "tokens_used": result_ai.get("tokens_used", 0),
    }

    await set_cached(cache_key, response, ttl_seconds=86400)
    return response


@router.post("/chat")
async def chat_with_atlas(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Ad-hoc chat queries to ATLAS. Uses claude-haiku-4-5."""
    from services.ai_copilot.copilot import chat_query
    from services.data_fetchers.cache_layer import get_cached

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    today = datetime.now(ET).strftime("%Y-%m-%d")
    context = await _build_snapshot_context(today, db)

    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    result = await chat_query(request.question, context, settings.anthropic_api_key, history)

    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "AI service error"))

    return {
        "response": result["content"],
        "model": result.get("model"),
        "tokens_used": result.get("tokens_used"),
    }


@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get recent AI-generated alerts from DB."""
    # Placeholder: in production these are written by the alert job
    from services.data_fetchers.cache_layer import get_cached
    alerts = await get_cached("recent_alerts") or []
    return {"alerts": alerts[:limit]}


async def _build_full_context(date_str: str, db) -> dict:
    """Assemble complete context dict for pre-market briefing generation."""
    import asyncio
    from services.data_fetchers.yahoo_fetcher import (
        fetch_es_daily, fetch_es_intraday_5min, fetch_vix_term_structure,
        fetch_crypto_overnight, fetch_dxy_overnight, get_es_spy_multiplier
    )
    from services.data_fetchers.fred_fetcher import fetch_all_macro
    from services.data_fetchers.cftc_fetcher import get_es_cot_analysis
    from services.data_fetchers.cboe_fetcher import get_pc_ratio_analysis
    from services.data_fetchers.calendar_fetcher import get_calendar_flags
    from services.gap_engine.gap_calculator import compute_gap_stats_for_session, classify_gap_size
    from services.gap_engine.gap_statistics import compute_fill_probability
    from services.data_fetchers.cache_layer import get_cached, set_cached
    from datetime import date

    # Run fetches in parallel
    tasks = await asyncio.gather(
        fetch_es_daily(years=2),
        fetch_vix_term_structure(),
        fetch_crypto_overnight(),
        fetch_dxy_overnight(),
        get_es_cot_analysis(),
        get_pc_ratio_analysis(),
        return_exceptions=True,
    )

    daily, vix_ts, crypto, dxy, cot, pc = [t if not isinstance(t, Exception) else None for t in tasks]

    # Load gap probability
    gap_prob = {}
    es_current = None
    on_high = on_low = None

    if daily is not None and len(daily) >= 2:
        today_row = daily.iloc[-1]
        prior_row = daily.iloc[-2]
        gap_stats = compute_gap_stats_for_session(today_row, prior_row)

        es_current = float(today_row.get("close", today_row.get("open", 0)))
        on_high = float(today_row["high"])  # Use daily high as ONH approximation
        on_low = float(today_row["low"])

        if gap_stats["gap_direction"] in ("up", "down"):
            gap_df = await _load_gap_df_from_db(db, 10)
            if gap_df is not None:
                prob_result = compute_fill_probability(
                    gap_df, gap_stats["gap_direction"],
                    gap_stats["gap_size_pts"] or 0
                )
                gap_prob = {**gap_stats, **prob_result}
            else:
                gap_prob = gap_stats

    # Macro
    macro = {}
    if settings.fred_api_key:
        try:
            macro = await fetch_all_macro(settings.fred_api_key)
        except Exception:
            pass

    # GEX levels from cache
    gex = await get_cached("gex_dashboard") or {}

    # Calendar
    try:
        cal_date = date.fromisoformat(date_str)
        cal = get_calendar_flags(cal_date)
    except Exception:
        cal = {}

    # Key levels from prior session
    levels = {}
    if daily is not None and len(daily) >= 2:
        pr = daily.iloc[-2]
        levels = {
            "prior_close": round(float(pr["close"]), 2),
            "pdh": round(float(pr["high"]), 2),
            "pdl": round(float(pr["low"]), 2),
        }

    return {
        "date": date_str,
        "day_name": date.fromisoformat(date_str).strftime("%A") if date_str else "",
        "es": {
            "current_price": es_current,
            "overnight_high": on_high,
            "overnight_low": on_low,
            "overnight_range": round(on_high - on_low, 2) if on_high and on_low else None,
        },
        "gap": gap_prob,
        "vix": vix_ts or {},
        "macro": macro,
        "gex": gex,
        "key_levels": levels,
        "calendar": cal,
        "cot": cot or {},
        "crypto": crypto or {},
        "dxy": dxy or {},
        "pc_ratio": pc or {},
    }


async def _build_snapshot_context(date_str: str, db) -> dict:
    """Lighter context for chat queries (no deep computation)."""
    from services.data_fetchers.cache_layer import get_cached
    from services.data_fetchers.yahoo_fetcher import fetch_vix_term_structure

    ctx = {}
    ctx["date"] = date_str
    ctx["gex"] = await get_cached("gex_dashboard") or {}
    ctx["vix"] = await fetch_vix_term_structure()
    ctx["gap"] = await get_cached(f"gap_today_{date_str}") or {}
    ctx["a_period"] = await get_cached("a_period_live") or {}
    return ctx


async def _load_gap_df_from_db(db, years):
    from sqlalchemy import select
    from models.database import DailySession
    from datetime import timedelta
    import pandas as pd

    cutoff = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    result = await db.execute(
        select(DailySession).where(
            DailySession.date >= cutoff,
            DailySession.excluded == False,
        ).order_by(DailySession.date)
    )
    rows = result.scalars().all()
    if not rows:
        return None

    data = [{c.key: getattr(row, c.key) for c in row.__table__.columns} for row in rows]
    return pd.DataFrame(data)
