"""
GEX (Gamma Exposure) Engine — Pillar 3.

Computes dealer gamma exposure from SPY options chain.
Identifies Call Wall, Put Wall, Zero Gamma level.
Classifies dealer regime: Long Gamma / Short Gamma / Neutral.

CRITICAL GEX SIGN CONVENTION (get this wrong = all regimes inverted):
Assumption: market makers are net SHORT options to the public
  - They are SHORT calls (sold calls to buyers) → when price rises, they must BUY to delta hedge
  - They are SHORT puts (sold puts to hedgers) → when price falls, they must SELL to delta hedge

Therefore:
  GEX_call_per_strike = +call_gamma × call_OI × 100 × spot² × 0.01
  GEX_put_per_strike = -put_gamma × put_OI × 100 × spot² × 0.01

Net GEX = Σ(GEX_call) + Σ(GEX_put)

Net GEX > 0: Market makers are net long gamma (calls dominate)
  → They BUY dips, SELL rips → SUPPRESS volatility → mean reversion

Net GEX < 0: Market makers are net short gamma (puts dominate)
  → They SELL dips, BUY rips → AMPLIFY volatility → trend continuation
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import logging

from services.options_engine.black_scholes import (
    black_scholes_greeks, implied_volatility, time_to_expiry_years
)

logger = logging.getLogger(__name__)


def compute_gex_from_chain(
    options_chain: dict,
    spot_price: float,
    risk_free_rate: float = 0.05,
) -> dict:
    """
    Main GEX computation entry point.
    options_chain: {"YYYY-MM-DD": {"calls": [...], "puts": [...], "expiration_ts": int}}
    Returns complete GEX profile.
    """
    if not options_chain or spot_price <= 0:
        return {}

    all_strike_gex = {}  # strike → net GEX
    total_call_gex = 0.0
    total_put_gex = 0.0
    unusual_activity = []

    now = datetime.utcnow()

    for exp_date, chain in options_chain.items():
        T = time_to_expiry_years(exp_date)
        if T <= 0:
            continue

        calls = chain.get("calls", [])
        puts = chain.get("puts", [])

        # Filter strikes within ±10% of spot
        strike_filter = lambda s: abs(s - spot_price) / spot_price <= 0.10

        for contract in calls:
            strike = float(contract.get("strike", 0) or 0)
            if not strike_filter(strike):
                continue

            oi = int(contract.get("open_interest", 0) or 0)
            volume = int(contract.get("volume", 0) or 0)
            if oi == 0:
                continue

            gamma = _get_or_compute_gamma(contract, spot_price, strike, T, risk_free_rate, "call")
            if gamma is None:
                continue

            # GEX formula: gamma × OI × 100 × spot² × 0.01
            # The 0.01 converts to "per 1% spot move" (industry standard)
            gex_call = gamma * oi * 100 * (spot_price ** 2) * 0.01
            total_call_gex += gex_call

            if strike not in all_strike_gex:
                all_strike_gex[strike] = {"call_gex": 0, "put_gex": 0, "call_oi": 0,
                                           "put_oi": 0, "call_vol": 0, "put_vol": 0,
                                           "call_gamma": 0, "put_gamma": 0}
            all_strike_gex[strike]["call_gex"] += gex_call
            all_strike_gex[strike]["call_oi"] += oi
            all_strike_gex[strike]["call_vol"] += volume
            all_strike_gex[strike]["call_gamma"] = max(all_strike_gex[strike]["call_gamma"], gamma)

            # Unusual activity detection
            if oi > 0 and volume / oi > 3.0:
                mid = (float(contract.get("bid", 0) or 0) + float(contract.get("ask", 0) or 0)) / 2
                premium = volume * mid * 100
                if premium >= 50000:
                    unusual_activity.append({
                        "type": "call",
                        "strike": strike,
                        "expiration": exp_date,
                        "volume": volume,
                        "oi": oi,
                        "vol_oi_ratio": round(volume / oi, 2),
                        "premium": round(premium),
                        "institutional": premium >= 50000,
                    })

        for contract in puts:
            strike = float(contract.get("strike", 0) or 0)
            if not strike_filter(strike):
                continue

            oi = int(contract.get("open_interest", 0) or 0)
            volume = int(contract.get("volume", 0) or 0)
            if oi == 0:
                continue

            gamma = _get_or_compute_gamma(contract, spot_price, strike, T, risk_free_rate, "put")
            if gamma is None:
                continue

            # Put GEX is NEGATIVE (sign convention: dealers long puts = short gamma)
            gex_put = -gamma * oi * 100 * (spot_price ** 2) * 0.01
            total_put_gex += gex_put

            if strike not in all_strike_gex:
                all_strike_gex[strike] = {"call_gex": 0, "put_gex": 0, "call_oi": 0,
                                           "put_oi": 0, "call_vol": 0, "put_vol": 0,
                                           "call_gamma": 0, "put_gamma": 0}
            all_strike_gex[strike]["put_gex"] += gex_put
            all_strike_gex[strike]["put_oi"] += oi
            all_strike_gex[strike]["put_vol"] += volume
            all_strike_gex[strike]["put_gamma"] = max(all_strike_gex[strike]["put_gamma"], gamma)

            if oi > 0 and volume / oi > 3.0:
                mid = (float(contract.get("bid", 0) or 0) + float(contract.get("ask", 0) or 0)) / 2
                premium = volume * mid * 100
                if premium >= 50000:
                    unusual_activity.append({
                        "type": "put",
                        "strike": strike,
                        "expiration": exp_date,
                        "volume": volume,
                        "oi": oi,
                        "vol_oi_ratio": round(volume / oi, 2),
                        "premium": round(premium),
                        "institutional": premium >= 50000,
                    })

    if not all_strike_gex:
        return {}

    # Build strike-level DataFrame
    strikes_df = pd.DataFrame([
        {
            "strike": strike,
            "call_gex": data["call_gex"],
            "put_gex": data["put_gex"],
            "net_gex": data["call_gex"] + data["put_gex"],
            "call_oi": data["call_oi"],
            "put_oi": data["put_oi"],
            "call_gamma": data["call_gamma"],
            "put_gamma": data["put_gamma"],
            "total_oi": data["call_oi"] + data["put_oi"],
        }
        for strike, data in all_strike_gex.items()
    ]).sort_values("strike").reset_index(drop=True)

    net_gex_total = total_call_gex + total_put_gex

    # Call Wall: strike with highest CALL gamma × OI (absolute resistance)
    call_wall_strike = _find_call_wall(strikes_df)

    # Put Wall: strike with highest PUT gamma × OI (support)
    put_wall_strike = _find_put_wall(strikes_df)

    # Zero Gamma Level: strike where cumulative GEX crosses zero
    zero_gamma_strike = _find_zero_gamma(strikes_df, spot_price)

    # Volatility Trigger: sharpest GEX sign change
    vol_trigger_strike = _find_vol_trigger(strikes_df)

    # Top 5 by absolute net GEX
    top_strikes = strikes_df.reindex(strikes_df["net_gex"].abs().nlargest(5).index)

    # Regime classification
    regime = _classify_regime(net_gex_total, strikes_df)

    # Sort unusual activity by premium
    unusual_activity.sort(key=lambda x: x["premium"], reverse=True)

    return {
        "net_gex": round(net_gex_total / 1e9, 4),  # In billions
        "net_gex_raw": net_gex_total,
        "total_call_gex": round(total_call_gex / 1e9, 4),
        "total_put_gex": round(total_put_gex / 1e9, 4),
        "call_wall_spy": call_wall_strike,
        "put_wall_spy": put_wall_strike,
        "zero_gamma_spy": zero_gamma_strike,
        "vol_trigger_spy": vol_trigger_strike,
        "regime": regime["name"],
        "regime_detail": regime,
        "strikes": strikes_df.to_dict("records"),
        "top_strikes": top_strikes[["strike", "net_gex", "call_oi", "put_oi"]].to_dict("records"),
        "unusual_activity": unusual_activity[:20],
        "spot_price": spot_price,
        "computed_at": datetime.utcnow().isoformat(),
    }


def _get_or_compute_gamma(
    contract: dict, spot: float, strike: float, T: float, r: float, opt_type: str
) -> Optional[float]:
    """Use provided gamma if available, otherwise compute via Black-Scholes."""
    gamma = float(contract.get("gamma", 0) or 0)
    if gamma > 0:
        return gamma

    # Compute via BS if IV available
    iv = float(contract.get("implied_volatility", 0) or 0)
    if iv <= 0:
        # Try computing IV from mid price
        bid = float(contract.get("bid", 0) or 0)
        ask = float(contract.get("ask", 0) or 0)
        mid = (bid + ask) / 2
        if mid > 0:
            iv = implied_volatility(mid, spot, strike, T, r, opt_type) or 0

    if iv > 0 and T > 0:
        greeks = black_scholes_greeks(spot, strike, T, r, iv, opt_type)
        return greeks.get("gamma", 0)

    return None


def _find_call_wall(df: pd.DataFrame) -> Optional[float]:
    """Call Wall = strike with highest call gamma × call OI product."""
    df_calls = df[df["call_oi"] > 0].copy()
    if df_calls.empty:
        return None
    df_calls["call_weighted"] = df_calls["call_gamma"] * df_calls["call_oi"]
    return float(df_calls.loc[df_calls["call_weighted"].idxmax(), "strike"])


def _find_put_wall(df: pd.DataFrame) -> Optional[float]:
    """Put Wall = strike with highest put gamma × put OI product."""
    df_puts = df[df["put_oi"] > 0].copy()
    if df_puts.empty:
        return None
    df_puts["put_weighted"] = df_puts["put_gamma"] * df_puts["put_oi"]
    return float(df_puts.loc[df_puts["put_weighted"].idxmax(), "strike"])


def _find_zero_gamma(df: pd.DataFrame, spot: float) -> Optional[float]:
    """
    Zero Gamma / Gamma Flip = price where cumulative GEX from below crosses zero.
    Computed by walking strikes from lowest to highest and tracking cumulative GEX.
    """
    if len(df) < 2:
        return None

    df_sorted = df.sort_values("strike").copy()
    cumulative = 0.0
    prev_strike = None
    prev_cum = None

    for _, row in df_sorted.iterrows():
        cumulative += row["net_gex"]
        if prev_cum is not None and prev_cum * cumulative < 0:
            # Interpolate zero crossing between prev_strike and current strike
            s1, s2 = prev_strike, row["strike"]
            c1, c2 = prev_cum, cumulative
            zero_cross = s1 + (s2 - s1) * (-c1) / (c2 - c1)
            return round(float(zero_cross), 2)
        prev_cum = cumulative
        prev_strike = row["strike"]

    return None


def _find_vol_trigger(df: pd.DataFrame) -> Optional[float]:
    """Volatility Trigger = strike where GEX changes sign most rapidly (max slope change)."""
    if len(df) < 3:
        return None

    df_sorted = df.sort_values("strike").copy()
    gex_values = df_sorted["net_gex"].values
    strikes = df_sorted["strike"].values

    max_change = 0.0
    trigger = None

    for i in range(1, len(gex_values) - 1):
        change = abs(gex_values[i + 1] - gex_values[i - 1])
        if change > max_change:
            max_change = change
            trigger = float(strikes[i])

    return trigger


def _classify_regime(net_gex: float, df: pd.DataFrame) -> dict:
    """
    Classify dealer gamma regime based on net GEX magnitude and sign.
    Neutral threshold = bottom 25th percentile of absolute GEX.
    """
    abs_gex_values = df["net_gex"].abs().values
    threshold = float(np.percentile(abs_gex_values, 25)) if len(abs_gex_values) > 0 else 0

    abs_net = abs(net_gex)

    if abs_net <= threshold:
        return {
            "name": "neutral",
            "label": "NEUTRAL GAMMA",
            "description": "Transition zone — regime change possible. High alert mode.",
            "volatility_bias": "uncertain",
            "trading_style": "reduce size, watch for regime confirmation",
            "es_behavior": "directional bias unclear, watch for breakout or rejection",
            "color": "#FF8C42",
        }
    elif net_gex > 0:
        return {
            "name": "long",
            "label": "LONG GAMMA",
            "description": "Dealers SUPPRESS volatility. Mean reversion likely.",
            "volatility_bias": "suppressed",
            "trading_style": "range trading, fade extremes, sell premium",
            "es_behavior": "contained moves, respects S/R, buy dips/sell rips",
            "color": "#10D982",
        }
    else:
        return {
            "name": "short",
            "label": "SHORT GAMMA",
            "description": "Dealers AMPLIFY volatility. Trend continuation likely.",
            "volatility_bias": "amplified",
            "trading_style": "breakout trades, momentum, buy premium",
            "es_behavior": "trends extend, breaks through levels, wider ranges",
            "color": "#FF3855",
        }


def convert_spy_to_es(spy_level: float, es_spy_multiplier: float) -> float:
    """Convert SPY-based level to ES equivalent using live multiplier."""
    return round(spy_level * es_spy_multiplier, 2)


def compute_skew_analysis(chain: dict, spot_price: float, r: float = 0.05) -> dict:
    """
    Put/Call skew: 25-delta put IV vs 25-delta call IV.
    Wider = fear, narrower = complacency.
    """
    results = {"25d_call_iv": None, "25d_put_iv": None, "skew": None, "interpretation": None}

    for exp_date, exp_data in chain.items():
        T = time_to_expiry_years(exp_date)
        if T < 7 / 365:  # Skip very short-dated for skew
            continue

        # Find 25-delta call and put
        calls = exp_data.get("calls", [])
        puts = exp_data.get("puts", [])

        call_25d = _find_nearest_delta_contract(calls, target_delta=0.25, opt_type="call",
                                                  spot=spot_price, T=T, r=r)
        put_25d = _find_nearest_delta_contract(puts, target_delta=-0.25, opt_type="put",
                                                 spot=spot_price, T=T, r=r)

        if call_25d and put_25d:
            results["25d_call_iv"] = call_25d.get("iv")
            results["25d_put_iv"] = put_25d.get("iv")
            if call_25d.get("iv") and put_25d.get("iv"):
                skew = put_25d["iv"] - call_25d["iv"]
                results["skew"] = round(skew * 100, 2)  # In vol points
                if skew > 0.05:
                    results["interpretation"] = "elevated_fear"
                elif skew < 0.01:
                    results["interpretation"] = "low_fear_complacency"
                else:
                    results["interpretation"] = "normal"
            break  # Use first valid expiration

    return results


def _find_nearest_delta_contract(contracts: list, target_delta: float, opt_type: str,
                                   spot: float, T: float, r: float) -> Optional[dict]:
    """Find the contract closest to target delta."""
    best = None
    best_diff = float("inf")

    for c in contracts:
        strike = float(c.get("strike", 0) or 0)
        if strike <= 0:
            continue

        iv = float(c.get("implied_volatility", 0) or 0)
        if iv <= 0:
            bid = float(c.get("bid", 0) or 0)
            ask = float(c.get("ask", 0) or 0)
            mid = (bid + ask) / 2
            iv = implied_volatility(mid, spot, strike, T, r, opt_type) or 0

        if iv > 0:
            greeks = black_scholes_greeks(spot, strike, T, r, iv, opt_type)
            delta = greeks.get("delta", 0)
            diff = abs(delta - target_delta)
            if diff < best_diff:
                best_diff = diff
                best = {"strike": strike, "delta": delta, "iv": iv, "gamma": greeks.get("gamma", 0)}

    return best if best_diff < 0.10 else None
