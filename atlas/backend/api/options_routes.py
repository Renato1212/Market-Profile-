"""Options / GEX API routes."""
from fastapi import APIRouter, HTTPException
from services.data_fetchers.cache_layer import get_cached, set_cached

router = APIRouter()


@router.get("/gex")
async def get_gex_dashboard():
    """Get live GEX data: regime, Call Wall, Put Wall, Zero Gamma, strike profile."""
    from services.data_fetchers.yahoo_fetcher import fetch_spy_options_chain, get_es_spy_multiplier
    from services.options_engine.gex_engine import compute_gex_from_chain, convert_spy_to_es
    from services.data_fetchers.fred_fetcher import fetch_fred_series
    from config import settings
    import asyncio

    cached = await get_cached("gex_dashboard")
    if cached:
        return cached

    chain_data, multiplier = await asyncio.gather(
        fetch_spy_options_chain(), get_es_spy_multiplier()
    )

    if chain_data is None:
        raise HTTPException(status_code=503, detail="Options data unavailable")

    spy_price = chain_data.get("spy_price", 0)
    chains = chain_data.get("chains", {})

    rf_rate = 0.05
    if settings.fred_api_key:
        rf_df = await fetch_fred_series("DGS3MO", settings.fred_api_key)
        if rf_df is not None and len(rf_df) > 0:
            rf_rate = float(rf_df.iloc[-1]["value"]) / 100

    gex_result = compute_gex_from_chain(chains, spy_price, rf_rate)

    if not gex_result:
        raise HTTPException(status_code=503, detail="GEX computation failed")

    gex_result["call_wall_es"] = convert_spy_to_es(gex_result["call_wall_spy"], multiplier) if gex_result.get("call_wall_spy") else None
    gex_result["put_wall_es"] = convert_spy_to_es(gex_result["put_wall_spy"], multiplier) if gex_result.get("put_wall_spy") else None
    gex_result["zero_gamma_es"] = convert_spy_to_es(gex_result["zero_gamma_spy"], multiplier) if gex_result.get("zero_gamma_spy") else None
    gex_result["es_spy_multiplier"] = round(multiplier, 4)

    await set_cached("gex_dashboard", gex_result, ttl_seconds=900)
    return gex_result


@router.get("/pc-ratio")
async def get_pc_ratio():
    """Get CBOE Put/Call ratio analysis."""
    from services.data_fetchers.cboe_fetcher import get_pc_ratio_analysis

    cached = await get_cached("pc_ratio")
    if cached:
        return cached

    result = await get_pc_ratio_analysis()
    if not result:
        raise HTTPException(status_code=503, detail="P/C ratio data unavailable")

    await set_cached("pc_ratio", result, ttl_seconds=3600)
    return result


@router.get("/unusual-activity")
async def get_unusual_activity():
    """Get unusual options activity (Vol/OI > 3.0, premium > $50k)."""
    from services.data_fetchers.yahoo_fetcher import fetch_spy_options_chain
    from services.options_engine.gex_engine import compute_gex_from_chain

    cached_val = await get_cached("unusual_activity")
    if cached_val:
        return cached_val

    chain_data = await fetch_spy_options_chain()
    if chain_data is None:
        raise HTTPException(status_code=503, detail="Options data unavailable")

    spy_price = chain_data.get("spy_price", 500)
    gex_result = compute_gex_from_chain(chain_data.get("chains", {}), spy_price)

    result = {
        "unusual_activity": gex_result.get("unusual_activity", []),
        "as_of": gex_result.get("computed_at"),
    }

    await set_cached("unusual_activity", result, ttl_seconds=900)
    return result


@router.get("/term-structure")
async def get_vix_term_structure():
    """Get VIX/VIX9D/VIX3M term structure analysis."""
    from services.data_fetchers.yahoo_fetcher import fetch_vix_term_structure

    cached = await get_cached("vix_term_structure")
    if cached:
        return cached

    result = await fetch_vix_term_structure()
    await set_cached("vix_term_structure", result, ttl_seconds=300)
    return result
