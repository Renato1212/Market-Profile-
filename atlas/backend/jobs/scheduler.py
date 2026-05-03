"""
APScheduler background jobs for ATLAS.
Handles: data refresh, GEX updates, DB population, AI alert generation.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import pytz

logger = logging.getLogger(__name__)
ET = pytz.timezone("America/New_York")


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=ET)

    # Daily: populate historical gap/A-period DB at 7:00 AM ET
    scheduler.add_job(
        populate_historical_db,
        CronTrigger(hour=7, minute=0, timezone=ET),
        id="populate_historical_db",
        replace_existing=True,
    )

    # Pre-market: generate AI briefing at 9:00 AM ET
    scheduler.add_job(
        generate_daily_briefing,
        CronTrigger(hour=9, minute=0, timezone=ET),
        id="daily_ai_briefing",
        replace_existing=True,
    )

    # Every 15 min during market hours: GEX update
    scheduler.add_job(
        refresh_gex,
        CronTrigger(minute="*/15", hour="9-16", day_of_week="mon-fri", timezone=ET),
        id="gex_refresh",
        replace_existing=True,
    )

    # Every 5 min during market hours: intraday data + alert check
    scheduler.add_job(
        run_intraday_refresh,
        CronTrigger(minute="*/5", hour="9-16", day_of_week="mon-fri", timezone=ET),
        id="intraday_refresh",
        replace_existing=True,
    )

    # Weekly: COT data on Friday afternoon
    scheduler.add_job(
        refresh_cot,
        CronTrigger(day_of_week="fri", hour=15, minute=30, timezone=ET),
        id="cot_refresh",
        replace_existing=True,
    )

    # Hourly cache cleanup
    scheduler.add_job(
        cleanup_cache,
        IntervalTrigger(hours=1),
        id="cache_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("ATLAS scheduler started with all jobs")
    return scheduler


async def populate_historical_db():
    """Build/update gap and A Period database from Yahoo Finance history."""
    from services.data_fetchers.yahoo_fetcher import fetch_es_daily, fetch_es_intraday_5min, fetch_yahoo
    from services.gap_engine.gap_calculator import build_gap_database
    from services.aperiod_engine.aperiod_classifier import compute_a_period_attributes
    from models.database import DailySession, IntradayBar, AsyncSessionLocal
    from sqlalchemy import select
    import asyncio

    logger.info("Starting historical DB population...")

    try:
        daily, intraday, vix = await asyncio.gather(
            fetch_es_daily(years=12),
            fetch_es_intraday_5min(days=60),
            fetch_yahoo("^VIX", interval="1d", range_="max"),
        )

        if daily is None:
            logger.error("Failed to fetch daily data")
            return

        gap_df = build_gap_database(daily, intraday, vix)
        if len(gap_df) == 0:
            logger.error("Gap database build returned empty")
            return

        # Bulk upsert to DB
        async with AsyncSessionLocal() as db:
            for _, row in gap_df.iterrows():
                existing = await db.execute(
                    select(DailySession).where(DailySession.date == str(row["date"]))
                )
                session = existing.scalar_one_or_none()

                row_dict = row.to_dict()
                # Remove computed fields not in model
                for extra in ["session_range_pct", "is_holiday"]:
                    row_dict.pop(extra, None)

                if session is None:
                    session = DailySession(**{k: v for k, v in row_dict.items()
                                              if k in DailySession.__table__.columns.keys()})
                    db.add(session)
                else:
                    for k, v in row_dict.items():
                        if k in DailySession.__table__.columns.keys() and k != "id":
                            setattr(session, k, v)

            await db.commit()

        # Also store intraday bars
        if intraday is not None:
            async with AsyncSessionLocal() as db:
                for _, bar in intraday.iterrows():
                    existing = await db.execute(
                        select(IntradayBar).where(
                            IntradayBar.date == str(bar["date"]),
                            IntradayBar.bar_index == int(bar["bar_index"])
                        )
                    )
                    existing_bar = existing.scalar_one_or_none()
                    if existing_bar is None:
                        new_bar = IntradayBar(
                            date=str(bar["date"]),
                            timestamp=str(bar.get("datetime_et", "")),
                            bar_index=int(bar["bar_index"]),
                            open=float(bar["open"]),
                            high=float(bar["high"]),
                            low=float(bar["low"]),
                            close=float(bar["close"]),
                            volume=float(bar.get("volume", 0) or 0),
                        )
                        db.add(new_bar)
                await db.commit()

        logger.info(f"Historical DB populated: {len(gap_df)} sessions")

    except Exception as e:
        logger.error(f"Historical DB population failed: {e}", exc_info=True)


async def refresh_gex():
    """Refresh GEX data from SPY options chain."""
    from services.data_fetchers.yahoo_fetcher import fetch_spy_options_chain, get_es_spy_multiplier
    from services.options_engine.gex_engine import compute_gex_from_chain, convert_spy_to_es
    from services.data_fetchers.cache_layer import set_cached
    from models.database import GEXSnapshot, AsyncSessionLocal
    import asyncio

    logger.info("Refreshing GEX...")
    try:
        chain_data, multiplier = await asyncio.gather(
            fetch_spy_options_chain(), get_es_spy_multiplier()
        )
        if chain_data is None:
            return

        spy_price = chain_data.get("spy_price", 0)
        gex_result = compute_gex_from_chain(chain_data.get("chains", {}), spy_price)

        if gex_result:
            gex_result["call_wall_es"] = convert_spy_to_es(gex_result.get("call_wall_spy", 0), multiplier)
            gex_result["put_wall_es"] = convert_spy_to_es(gex_result.get("put_wall_spy", 0), multiplier)
            gex_result["zero_gamma_es"] = convert_spy_to_es(gex_result.get("zero_gamma_spy", 0), multiplier)
            gex_result["es_spy_multiplier"] = round(multiplier, 4)

            await set_cached("gex_dashboard", gex_result, ttl_seconds=900)

            # Persist snapshot
            import json
            async with AsyncSessionLocal() as db:
                from datetime import datetime
                snapshot = GEXSnapshot(
                    timestamp=datetime.utcnow().isoformat(),
                    spy_price=spy_price,
                    net_gex=gex_result.get("net_gex_raw", 0),
                    call_wall_spy=gex_result.get("call_wall_spy"),
                    put_wall_spy=gex_result.get("put_wall_spy"),
                    zero_gamma_spy=gex_result.get("zero_gamma_spy"),
                    call_wall_es=gex_result.get("call_wall_es"),
                    put_wall_es=gex_result.get("put_wall_es"),
                    zero_gamma_es=gex_result.get("zero_gamma_es"),
                    regime=gex_result.get("regime", "neutral"),
                )
                db.add(snapshot)
                await db.commit()

            logger.info(f"GEX refreshed: {gex_result.get('regime')} gamma, net={gex_result.get('net_gex')}")

    except Exception as e:
        logger.error(f"GEX refresh failed: {e}", exc_info=True)


async def run_intraday_refresh():
    """
    5-minute intraday refresh: update price data, check alert thresholds.
    Runs every 5 min during market hours.
    """
    from services.data_fetchers.yahoo_fetcher import fetch_yahoo, fetch_vix_term_structure
    from services.data_fetchers.cache_layer import set_cached, get_cached
    from datetime import datetime
    import pytz

    try:
        # Refresh market snapshot
        es_bars = await fetch_yahoo("ES=F", interval="1m", range_="1d")
        if es_bars is not None and len(es_bars) > 0:
            es_price = float(es_bars.iloc[-1]["close"])
            await set_cached("es_current_price", es_price, ttl_seconds=120)

        logger.debug("Intraday refresh complete")

    except Exception as e:
        logger.error(f"Intraday refresh failed: {e}")


async def generate_daily_briefing():
    """Generate and cache the daily pre-market AI briefing at 9:00 AM ET."""
    from models.database import AsyncSessionLocal
    import asyncio

    try:
        async with AsyncSessionLocal() as db:
            from api.ai_routes import _build_full_context
            from services.ai_copilot.copilot import generate_premarket_briefing
            from services.data_fetchers.cache_layer import set_cached
            from config import settings
            from datetime import datetime
            import pytz

            today = datetime.now(pytz.timezone("America/New_York")).strftime("%Y-%m-%d")

            if not settings.anthropic_api_key:
                logger.warning("Skipping AI briefing — ANTHROPIC_API_KEY not set")
                return

            context = await _build_full_context(today, db)
            result = await generate_premarket_briefing(context, settings.anthropic_api_key)

            if result.get("success"):
                from models.database import AIBriefing
                briefing = AIBriefing(
                    date=today,
                    content=result["content"],
                    model_used=result.get("model", ""),
                    tokens_used=result.get("tokens_used", 0),
                )
                db.add(briefing)
                await db.commit()
                await set_cached(f"ai_briefing_{today}", {"content": result["content"], "date": today}, 86400)
                logger.info(f"Daily briefing generated for {today}")

    except Exception as e:
        logger.error(f"Daily briefing generation failed: {e}", exc_info=True)


async def refresh_cot():
    """Refresh COT data (weekly, Fridays)."""
    from services.data_fetchers.cftc_fetcher import get_es_cot_analysis
    from services.data_fetchers.cache_layer import set_cached

    try:
        result = await get_es_cot_analysis()
        await set_cached("cot_data", result, ttl_seconds=604800)
        logger.info("COT data refreshed")
    except Exception as e:
        logger.error(f"COT refresh failed: {e}")


async def cleanup_cache():
    """Remove expired cache entries."""
    from services.data_fetchers.cache_layer import _cache
    await _cache.clear_expired()
