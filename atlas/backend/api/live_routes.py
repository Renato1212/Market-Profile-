"""Live session management routes."""
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/refresh")
async def trigger_data_refresh():
    """Manually trigger a data refresh cycle."""
    from jobs.scheduler import run_intraday_refresh
    try:
        await run_intraday_refresh()
        return {"status": "ok", "message": "Refresh triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_live_status():
    """Get current session status and last update times."""
    from services.data_fetchers.cache_layer import get_cached
    from datetime import datetime
    import pytz

    ET = pytz.timezone("America/New_York")
    now_et = datetime.now(ET)

    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    in_session = (market_open <= now_et <= market_close and now_et.weekday() < 5)
    in_a_period = (market_open <= now_et < now_et.replace(hour=10, minute=0, second=0, microsecond=0))

    gex_data = await get_cached("gex_dashboard") or {}
    snapshot = await get_cached("market_snapshot") or {}

    return {
        "current_time_et": now_et.strftime("%H:%M:%S ET"),
        "in_session": in_session,
        "in_a_period": in_a_period,
        "session_phase": _get_session_phase(now_et),
        "data_freshness": {
            "gex_as_of": gex_data.get("computed_at"),
            "snapshot_as_of": snapshot.get("timestamp"),
        },
    }


def _get_session_phase(now_et) -> str:
    h, m = now_et.hour, now_et.minute
    if h < 9 or (h == 9 and m < 30):
        return "pre_market"
    elif h == 9 and m < 60 and m >= 30:
        return "a_period" if m < 60 else "post_a"
    elif h < 10:
        return "a_period"
    elif h < 12:
        return "morning"
    elif h < 14:
        return "midday"
    elif h < 16:
        return "afternoon"
    else:
        return "after_hours"
