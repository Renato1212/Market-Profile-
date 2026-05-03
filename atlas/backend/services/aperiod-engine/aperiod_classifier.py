"""
A Period Auction Analytics Engine — Pillar 2.

A Period = 09:30:00 to 10:00:00 ET (six 5-min bars exactly).
Initial Balance = 09:30 to 10:30 ET (twelve 5-min bars).

CRITICAL: timing must be precise.
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# A Period type constants
OPEN_DRIVE = "open_drive"
OPEN_TEST_DRIVE = "open_test_drive"
OPEN_AUCTION = "open_auction"
OPEN_REJECTION_REVERSE = "open_rejection_reverse"
OPEN_GAP = "open_gap"
NARROW_A_PERIOD = "narrow_a_period"
VOLATILE_OPEN = "volatile_open"


def classify_a_period_type(
    bars: pd.DataFrame,  # Exactly 6 5-min bars (09:30–10:00)
    prior_close: Optional[float] = None,
    vah: Optional[float] = None,
    val: Optional[float] = None,
    pdh: Optional[float] = None,
    pdl: Optional[float] = None,
    avg_range_20d: Optional[float] = None,
) -> dict:
    """
    Classify the A Period type using the 7-type taxonomy.
    Returns type + all supporting attributes.
    """
    if bars is None or len(bars) < 6:
        return {"a_type": None, "error": "insufficient_bars"}

    bars = bars.sort_values("bar_index").head(6).reset_index(drop=True)

    a_open = float(bars.iloc[0]["open"])
    a_high = float(bars["high"].max())
    a_low = float(bars["low"].min())
    a_close = float(bars.iloc[-1]["close"])
    a_range = a_high - a_low
    a_volume = float(bars["volume"].sum())

    body = abs(a_close - a_open)
    body_vs_range = body / a_range if a_range > 0 else 0
    close_position = (a_close - a_low) / a_range * 100 if a_range > 0 else 50

    direction = "bullish" if a_close > a_open else ("bearish" if a_close < a_open else "neutral")

    # Range relative to 20-day average
    range_percentile = None
    volatile_flag = False
    narrow_flag = False
    if avg_range_20d and avg_range_20d > 0:
        range_ratio = a_range / avg_range_20d
        volatile_flag = range_ratio > 2.0
        narrow_flag = range_ratio < 0.50
    else:
        range_ratio = None

    # Key reference tests (within 1 point of level)
    ref_test_threshold = 1.0
    tested_level = None
    if prior_close and abs(a_open - prior_close) <= ref_test_threshold:
        tested_level = "prior_close"
    elif vah and abs(a_high - vah) <= ref_test_threshold:
        tested_level = "vah"
    elif val and abs(a_low - val) <= ref_test_threshold:
        tested_level = "val"
    elif pdh and abs(a_high - pdh) <= ref_test_threshold:
        tested_level = "pdh"
    elif pdl and abs(a_low - pdl) <= ref_test_threshold:
        tested_level = "pdl"

    # Gap classification (significant gap = >5 pts)
    has_gap = prior_close and abs(a_open - prior_close) > 5.0

    # Determine type — check in priority order
    a_type = _determine_type(
        a_open, a_high, a_low, a_close, a_range,
        body_vs_range, close_position, direction,
        volatile_flag, narrow_flag, has_gap, tested_level,
        prior_close, bars
    )

    # Relative to reference levels
    attrs = {
        "a_open": round(a_open, 2),
        "a_high": round(a_high, 2),
        "a_low": round(a_low, 2),
        "a_close": round(a_close, 2),
        "a_range": round(a_range, 2),
        "a_volume": a_volume,
        "a_close_position": round(close_position, 1),
        "a_body_vs_range": round(body_vs_range, 3),
        "a_direction": direction,
        "a_type": a_type,
        "range_ratio_vs_20d": round(range_ratio, 3) if range_ratio else None,
    }

    # Reference level proximity
    if vah:
        attrs["a_vs_vah"] = round(a_close - vah, 2)
        attrs["vah_acceptance"] = _check_acceptance(bars, vah)
    if val:
        attrs["a_vs_val"] = round(a_close - val, 2)
        attrs["val_acceptance"] = _check_acceptance(bars, val)
    if pdh:
        attrs["a_vs_pdh"] = round(a_close - pdh, 2)
    if pdl:
        attrs["a_vs_pdl"] = round(a_close - pdl, 2)
    if prior_close:
        attrs["gap_filled_in_a_period"] = (
            (a_open > prior_close and a_low <= prior_close) or
            (a_open < prior_close and a_high >= prior_close)
        )

    return attrs


def _determine_type(
    a_open, a_high, a_low, a_close, a_range,
    body_vs_range, close_position, direction,
    volatile_flag, narrow_flag, has_gap, tested_level,
    prior_close, bars
) -> str:
    """Priority-ordered type classification."""

    # Volatile Open takes precedence when range is extreme
    if volatile_flag:
        return VOLATILE_OPEN

    # Narrow A Period when range is very compressed
    if narrow_flag:
        return NARROW_A_PERIOD

    # Open-Gap when significant gap exists
    if has_gap:
        return OPEN_GAP

    # Open-Rejection-Reverse: initial direction reverses
    initial_direction = "up" if bars.iloc[0]["close"] > a_open else "down"
    final_direction = "up" if a_close > a_open else "down"
    reversal = initial_direction != final_direction and body_vs_range > 0.30
    if reversal and close_position not in range(30, 70):
        return OPEN_REJECTION_REVERSE

    # Open-Test-Drive: tests a key level then drives opposite
    if tested_level and body_vs_range > 0.45:
        if (close_position > 80) or (close_position < 20):
            return OPEN_TEST_DRIVE

    # Open-Drive: strong directional move, conviction
    if body_vs_range > 0.60 and (close_position > 80 or close_position < 20):
        return OPEN_DRIVE

    # Open-Auction: two-timeframe, rotational
    if 30 <= close_position <= 70 and body_vs_range < 0.35:
        return OPEN_AUCTION

    # Default to Open-Auction if no other type fits
    return OPEN_AUCTION


def _check_acceptance(bars: pd.DataFrame, level: float, threshold: float = 1.0) -> bool:
    """Level acceptance = price traded within threshold for >1 bar."""
    bars_at_level = bars[
        (bars["low"] <= level + threshold) & (bars["high"] >= level - threshold)
    ]
    return len(bars_at_level) > 1


def compute_a_period_attributes(
    intraday_df: pd.DataFrame,
    date_str: str,
    session_row: pd.Series,
    prior_row: Optional[pd.Series] = None,
    vah: Optional[float] = None,
    val: Optional[float] = None,
    poc: Optional[float] = None,
    avg_range_20d: Optional[float] = None,
) -> dict:
    """
    Full A Period attribute computation for one session.
    Extracts A Period bars (09:30–10:00, bar_index 0-5) from intraday data.
    """
    if intraday_df is None or len(intraday_df) == 0:
        return {}

    day_bars = intraday_df[intraday_df["date"] == date_str].sort_values("bar_index")

    # A Period = first 6 bars (09:30, 09:35, 09:40, 09:45, 09:50, 09:55)
    a_bars = day_bars[day_bars["bar_index"] < 6]

    if len(a_bars) < 6:
        return {}

    # Initial Balance = first 12 bars (09:30–10:30)
    ib_bars = day_bars[day_bars["bar_index"] < 12]

    prior_close = float(prior_row["close"]) if prior_row is not None else None
    pdh = float(prior_row["high"]) if prior_row is not None else None
    pdl = float(prior_row["low"]) if prior_row is not None else None

    # On session high/low (Globex) — from session_row or approximated
    on_high = float(session_row.get("on_high", session_row.get("high", 0)) or 0)
    on_low = float(session_row.get("on_low", session_row.get("low", 0)) or 0)

    attrs = classify_a_period_type(
        a_bars, prior_close=prior_close, vah=vah, val=val,
        pdh=pdh, pdl=pdl, avg_range_20d=avg_range_20d
    )

    # Session outcome checks (computed after full session data available)
    session_high = float(session_row["high"])
    session_low = float(session_row["low"])
    a_high = attrs.get("a_high", 0)
    a_low = attrs.get("a_low", 0)

    attrs["a_high_held_eod"] = session_high <= a_high * 1.0001  # A High held all day
    attrs["a_low_held_eod"] = session_low >= a_low * 0.9999    # A Low held all day

    # Extension direction
    broke_high = session_high > a_high
    broke_low = session_low < a_low
    if broke_high and broke_low:
        attrs["a_extension_direction"] = "both"
    elif broke_high:
        attrs["a_extension_direction"] = "high"
    elif broke_low:
        attrs["a_extension_direction"] = "low"
    else:
        attrs["a_extension_direction"] = "neither"

    # ONH/ONL break in A Period
    if on_high > 0:
        attrs["onh_break"] = attrs["a_high"] >= on_high
    if on_low > 0:
        attrs["onl_break"] = attrs["a_low"] <= on_low

    # Initial Balance stats
    if len(ib_bars) >= 12:
        attrs["ib_high"] = round(float(ib_bars["high"].max()), 2)
        attrs["ib_low"] = round(float(ib_bars["low"].min()), 2)
        attrs["ib_range"] = round(attrs["ib_high"] - attrs["ib_low"], 2)

    # Day type classification (full session required)
    attrs["day_type"] = classify_day_type_full(session_row, a_bars, day_bars)

    return attrs


def classify_day_type_full(session_row: pd.Series, a_bars: pd.DataFrame, all_bars: pd.DataFrame) -> str:
    """
    Full session day type classification using A Period structure + session shape.
    Returns one of: trend_up, trend_down, normal_up, normal_down, neutral,
    double_distribution, trend_reversal
    """
    if len(all_bars) == 0:
        return "unknown"

    open_p = float(session_row["open"])
    close = float(session_row["close"])
    high = float(session_row["high"])
    low = float(session_row["low"])
    session_range = high - low

    if session_range < 0.01:
        return "unknown"

    close_position = (close - low) / session_range
    body = abs(close - open_p)
    body_pct = body / session_range

    # Check for double distribution (two distinct price clusters)
    is_double_dist = _detect_double_distribution(all_bars, session_range)
    if is_double_dist:
        return "double_distribution"

    # Trend day: body > 70%, closes in extreme 25%, large range
    if body_pct > 0.70:
        if close_position > 0.75:
            return "trend_up"
        elif close_position < 0.25:
            return "trend_down"

    # Normal day: moderate range, balanced close
    if 0.30 < close_position < 0.70 and body_pct < 0.50:
        return "normal_up" if close > open_p else "normal_down"

    # Trend + Reversal: opened strongly, reversed
    if len(a_bars) >= 6:
        a_close = float(a_bars.iloc[-1]["close"])
        a_open = float(a_bars.iloc[0]["open"])
        a_direction_up = a_close > a_open
        session_direction_up = close > open_p
        if a_direction_up != session_direction_up and body_pct > 0.35:
            return "trend_reversal"

    return "neutral"


def _detect_double_distribution(bars: pd.DataFrame, session_range: float) -> bool:
    """
    Detect double distribution pattern: two distinct volume clusters separated by a gap.
    Uses histogram of closes with gap detection in middle third.
    """
    if len(bars) < 20 or session_range < 2:
        return False

    closes = bars["close"].values
    low = closes.min()
    high = closes.max()

    if high - low < 0.01:
        return False

    n_bins = 20
    hist, bin_edges = np.histogram(closes, bins=n_bins, range=(low, high))

    # Check for a clear trough in the middle third
    middle_start = n_bins // 3
    middle_end = 2 * n_bins // 3
    middle_hist = hist[middle_start:middle_end]
    outer_hist = np.concatenate([hist[:middle_start], hist[middle_end:]])

    if len(outer_hist) == 0 or outer_hist.mean() == 0:
        return False

    # Double distribution if middle is significantly lower than outer zones
    return middle_hist.mean() < outer_hist.mean() * 0.4


def predict_day_type_live(
    current_a_bars: pd.DataFrame,
    open_location: str,
    on_break_high: bool = False,
    on_break_low: bool = False,
    historical_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Live day type prediction during A Period.
    Updates every 5 minutes with new bars.
    Returns probability distribution.

    Weighted model:
    - A Close Position: 30%
    - A Period Type: 25%
    - Open Location vs VA: 20%
    - A Range Percentile: 15%
    - ONH/ONL Break: 10%
    """
    if len(current_a_bars) == 0:
        return {"probabilities": {}, "top_prediction": None, "confidence": "insufficient"}

    bars = current_a_bars.sort_values("bar_index")
    a_open = float(bars.iloc[0]["open"])
    a_high = float(bars["high"].max())
    a_low = float(bars["low"].min())
    a_close = float(bars.iloc[-1]["close"])
    a_range = a_high - a_low

    close_pos = ((a_close - a_low) / a_range * 100) if a_range > 0 else 50
    body_ratio = abs(a_close - a_open) / a_range if a_range > 0 else 0

    # Score components → weighted toward each day type
    scores = {
        "trend_up": 0.0,
        "trend_down": 0.0,
        "normal_up": 0.0,
        "normal_down": 0.0,
        "neutral": 0.0,
    }

    # A Close Position weight (30%)
    if close_pos > 80:
        scores["trend_up"] += 0.30
    elif close_pos > 66:
        scores["trend_up"] += 0.18
        scores["normal_up"] += 0.12
    elif close_pos < 20:
        scores["trend_down"] += 0.30
    elif close_pos < 34:
        scores["trend_down"] += 0.18
        scores["normal_down"] += 0.12
    else:
        scores["neutral"] += 0.30
        scores["normal_up"] += 0.15
        scores["normal_down"] += 0.15

    # A Period Type weight (25%)
    if body_ratio > 0.60 and (close_pos > 80 or close_pos < 20):
        if close_pos > 80:
            scores["trend_up"] += 0.25
        else:
            scores["trend_down"] += 0.25
    elif 30 <= close_pos <= 70 and body_ratio < 0.35:
        scores["neutral"] += 0.15
        scores["normal_up"] += 0.05
        scores["normal_down"] += 0.05
    else:
        scores["normal_up"] += 0.10
        scores["normal_down"] += 0.10
        scores["neutral"] += 0.05

    # Open Location weight (20%)
    location_scores = {
        "above_vah": {"trend_up": 0.15, "normal_up": 0.05},
        "below_val": {"trend_down": 0.15, "normal_down": 0.05},
        "in_value_upper": {"normal_up": 0.12, "trend_up": 0.08},
        "in_value_lower": {"normal_down": 0.12, "trend_down": 0.08},
        "at_poc": {"neutral": 0.15, "normal_up": 0.025, "normal_down": 0.025},
    }
    for day_type, bonus in location_scores.get(open_location, {"neutral": 0.10}).items():
        scores[day_type] = scores.get(day_type, 0) + bonus

    # ONH/ONL Break weight (10%)
    if on_break_high:
        scores["trend_up"] += 0.10
    elif on_break_low:
        scores["trend_down"] += 0.10
    else:
        scores["neutral"] += 0.05
        scores["normal_up"] += 0.025
        scores["normal_down"] += 0.025

    # Normalize to sum to 1
    total = sum(scores.values())
    if total > 0:
        probs = {k: round(v / total * 100, 1) for k, v in scores.items()}
    else:
        probs = {k: 20.0 for k in scores}

    top = max(probs, key=probs.get)
    top_pct = probs[top]

    confidence = "high" if top_pct > 55 else ("medium" if top_pct > 40 else "low")

    return {
        "probabilities": probs,
        "top_prediction": top,
        "top_probability_pct": top_pct,
        "confidence": confidence,
        "bars_used": len(bars),
        "a_close_position": round(close_pos, 1),
        "a_range": round(a_range, 2),
    }
