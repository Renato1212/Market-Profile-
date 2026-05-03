"""
Tradier Sandbox API fetcher — free tier, options data backup.
Free sandbox account required (no billing).
15-min delayed data in sandbox.
"""
import httpx
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

TRADIER_SANDBOX_BASE = "https://sandbox.tradier.com/v1"
TRADIER_PROD_BASE = "https://api.tradier.com/v1"


async def fetch_tradier_options_chain(
    symbol: str,
    expiration: str,
    token: str,
    sandbox: bool = True,
) -> Optional[dict]:
    """
    Fetch options chain from Tradier.
    expiration: YYYY-MM-DD format
    Returns dict with 'calls' and 'puts' lists.
    """
    base = TRADIER_SANDBOX_BASE if sandbox else TRADIER_PROD_BASE
    url = f"{base}/markets/options/chains"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        "symbol": symbol,
        "expiration": expiration,
        "greeks": "true",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                options = data.get("options", {})
                if not options or options == "null":
                    return None

                option_list = options.get("option", [])
                if isinstance(option_list, dict):
                    option_list = [option_list]

                calls = [o for o in option_list if o.get("option_type") == "call"]
                puts = [o for o in option_list if o.get("option_type") == "put"]

                return {
                    "symbol": symbol,
                    "expiration": expiration,
                    "calls": _normalize_tradier_options(calls),
                    "puts": _normalize_tradier_options(puts),
                }

            except Exception as e:
                logger.error(f"Tradier fetch error attempt {attempt+1}: {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return None


def _normalize_tradier_options(options: list) -> list:
    """Normalize Tradier option objects to standard format."""
    normalized = []
    for o in options:
        try:
            greeks = o.get("greeks", {}) or {}
            normalized.append({
                "strike": float(o.get("strike", 0)),
                "bid": float(o.get("bid", 0) or 0),
                "ask": float(o.get("ask", 0) or 0),
                "mid": (float(o.get("bid", 0) or 0) + float(o.get("ask", 0) or 0)) / 2,
                "volume": int(o.get("volume", 0) or 0),
                "open_interest": int(o.get("open_interest", 0) or 0),
                "implied_volatility": float(o.get("greeks", {}).get("mid_iv", 0) or 0) if greeks else 0,
                "delta": float(greeks.get("delta", 0) or 0),
                "gamma": float(greeks.get("gamma", 0) or 0),
                "theta": float(greeks.get("theta", 0) or 0),
                "vega": float(greeks.get("vega", 0) or 0),
                "expiration": o.get("expiration_date", ""),
                "last": float(o.get("last", 0) or 0),
            })
        except (ValueError, TypeError):
            continue
    return normalized


async def fetch_tradier_expirations(symbol: str, token: str, sandbox: bool = True) -> list:
    """Fetch available option expiration dates for a symbol."""
    base = TRADIER_SANDBOX_BASE if sandbox else TRADIER_PROD_BASE
    url = f"{base}/markets/options/expirations"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"symbol": symbol, "includeAllRoots": "false"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            expirations = data.get("expirations", {})
            if expirations:
                dates = expirations.get("date", [])
                return dates if isinstance(dates, list) else [dates]
        except Exception as e:
            logger.error(f"Tradier expirations error: {e}")
    return []
