"""
Gap Fill Statistical Engine — Pillar 1.

CRITICAL CORRECTNESS RULES (never violate):
- Gap = cash open vs PRIOR cash close. Uses 09:30 open vs prior 16:00 close.
- Gap Up FILLED if and only if: session LOW ≤ prior close (traded through)
- Gap Down FILLED if and only if: session HIGH ≥ prior close (traded through)
- Gaps across holiday closures are EXCLUDED.
- Prior session is the last valid trading day (not necessarily yesterday).
"""
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
import logging

from services.data_fetchers.calendar_fetcher import (
    is_market_holiday, get_prior_trading_day, get_calendar_flags,
    is_fomc_day, is_fomc_eve, is_opex_friday, is_quarter_end, is_expiry_week
)

logger = logging.getLogger(__name__)

MIN_GAP_TICKS = 0.25  # 1 tick = minimum gap to classify
MAX_SESSION_MOVE_PCT = 0.15  # Exclude sessions with >15% moves (bad data)


def classify_gap_context(open_price: float, vah: Optional[float], val: Optional[float],
                          poc: Optional[float], pdh: Optional[float], pdl: Optional[float]) -> str:
    """Classify opening location relative to Value Area and prior range."""
    if vah is None or val is None:
        if pdh is not None and open_price > pdh:
            return "above_pdh"
        if pdl is not None and open_price < pdl:
            return "below_pdl"
        return "inside_prior_range"

    va_range = vah - val
    va_upper = val + va_range * 0.75
    va_lower = val + va_range * 0.25

    if open_price > vah:
        return "above_vah"
    elif open_price >= va_upper:
        return "in_value_upper"
    elif open_price >= va_lower:
        return "at_poc" if (poc and abs(open_price - poc) <= va_range * 0.1) else "in_value_mid"
    elif open_price >= val:
        return "in_value_lower"
    else:
        return "below_val"


def classify_day_type(row: pd.Series) -> str:
    """Classify prior session type based on OHLC structure."""
    if pd.isna(row.get("open")) or pd.isna(row.get("close")):
        return "unknown"

    open_p = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    session_range = high - low

    if session_range < 1e-6:
        return "unknown"

    body = abs(close - open_p)
    body_pct = body / session_range
    close_position = (close - low) / session_range  # 0 = at low, 1 = at high

    # Trend Up: body > 60%, closes in upper 30%
    if body_pct > 0.60 and close_position > 0.70:
        return "trend_up"
    # Trend Down: body > 60%, closes in lower 30%
    elif body_pct > 0.60 and close_position < 0.30:
        return "trend_down"
    # Normal: medium body, close in middle area
    elif 0.25 < close_position < 0.75 and body_pct < 0.55:
        return "normal"
    # Outside Day: high > prior high and low < prior low
    # (requires context — mark as normal for now, refined in engine)
    else:
        return "normal_variation"


def compute_sma_regime(closes: pd.Series) -> str:
    """Classify trend regime using SMA stack: 20/50/200."""
    if len(closes) < 200:
        return "insufficient_data"
    sma20 = closes.tail(20).mean()
    sma50 = closes.tail(50).mean()
    sma200 = closes.tail(200).mean()
    current = float(closes.iloc[-1])

    if current > sma20 > sma50 > sma200:
        return "bull"
    elif current < sma20 < sma50 < sma200:
        return "bear"
    else:
        return "mixed"


def compute_gap_stats_for_session(
    session_row: pd.Series,
    prior_row: pd.Series,
    intraday_bars: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Compute all gap statistics for a single trading session.
    Returns dict of gap fields.
    CRITICAL: This is the ground truth. Get this right or everything is wrong.
    """
    stats = {
        "gap_size_pts": None,
        "gap_size_pct": None,
        "gap_direction": "none",
        "filled_same_session": None,
        "fill_time_minutes": None,
        "mae_before_fill_pts": None,
        "partial_fill_25pct": None,
        "partial_fill_50pct": None,
        "partial_fill_75pct": None,
        "gap_context": None,
    }

    if pd.isna(prior_row.get("close")) or pd.isna(session_row.get("open")):
        return stats

    prior_close = float(prior_row["close"])
    session_open = float(session_row["open"])
    session_high = float(session_row["high"])
    session_low = float(session_row["low"])

    gap_pts = session_open - prior_close
    gap_pct = gap_pts / prior_close * 100 if prior_close != 0 else 0

    if abs(gap_pts) < MIN_GAP_TICKS:
        return stats

    direction = "up" if gap_pts > 0 else "down"
    stats["gap_size_pts"] = round(abs(gap_pts), 2)
    stats["gap_size_pct"] = round(abs(gap_pct), 4)
    stats["gap_direction"] = direction

    # CRITICAL GAP FILL LOGIC — do not simplify
    if direction == "up":
        # Gap Up filled if LOW trades BACK DOWN through prior close
        filled = session_low <= prior_close
        # Partial fills (how far price moved back toward prior close)
        gap_to_fill = session_open - prior_close
        if gap_to_fill > 0:
            stats["partial_fill_25pct"] = session_low <= (session_open - gap_to_fill * 0.25)
            stats["partial_fill_50pct"] = session_low <= (session_open - gap_to_fill * 0.50)
            stats["partial_fill_75pct"] = session_low <= (session_open - gap_to_fill * 0.75)
    else:
        # Gap Down filled if HIGH trades BACK UP through prior close
        filled = session_high >= prior_close
        gap_to_fill = prior_close - session_open
        if gap_to_fill > 0:
            stats["partial_fill_25pct"] = session_high >= (session_open + gap_to_fill * 0.25)
            stats["partial_fill_50pct"] = session_high >= (session_open + gap_to_fill * 0.50)
            stats["partial_fill_75pct"] = session_high >= (session_open + gap_to_fill * 0.75)

    stats["filled_same_session"] = filled

    # Intraday precision: fill time and MAE before fill
    if intraday_bars is not None and len(intraday_bars) > 0 and filled:
        fill_bar, fill_time_min, mae = _find_fill_details(
            intraday_bars, prior_close, direction, session_open
        )
        stats["fill_time_minutes"] = fill_time_min
        stats["mae_before_fill_pts"] = mae

    return stats


def _find_fill_details(bars: pd.DataFrame, prior_close: float, direction: str,
                       session_open: float) -> tuple:
    """
    Find the exact 5-min bar where gap fill occurred and compute MAE.
    MAE = max adverse excursion (how far price moved AWAY from fill before filling).
    """
    fill_bar_idx = None
    mae = 0.0

    for i, (_, bar) in enumerate(bars.iterrows()):
        bar_low = float(bar["low"])
        bar_high = float(bar["high"])

        if direction == "up":
            # Track max move AWAY from fill (upward) before fill
            if bar_high > session_open:
                mae = max(mae, bar_high - session_open)
            if bar_low <= prior_close:
                fill_bar_idx = i
                break
        else:
            # Track max move AWAY from fill (downward) before fill
            if bar_low < session_open:
                mae = max(mae, session_open - bar_low)
            if bar_high >= prior_close:
                fill_bar_idx = i
                break

    if fill_bar_idx is None:
        return None, None, None

    # Each bar is 5 minutes, starting at 09:30
    fill_time_minutes = (fill_bar_idx + 1) * 5  # End of bar

    return fill_bar_idx, fill_time_minutes, round(mae, 2)


def classify_gap_size(gap_pts: float) -> str:
    """Bucket gap by size for Table B statistics."""
    if gap_pts < 3:
        return "micro"
    elif gap_pts < 8:
        return "small"
    elif gap_pts < 20:
        return "medium"
    elif gap_pts < 40:
        return "large"
    else:
        return "extreme"


def compute_consecutive_gap_streak(gap_series: pd.Series) -> pd.Series:
    """
    For each session, compute consecutive gap streak in same direction.
    Positive = up streak, negative = down streak, 0 = reversal/no gap.
    """
    result = []
    streak = 0
    last_direction = None

    for direction in gap_series:
        if direction == "none" or pd.isna(direction):
            streak = 0
            last_direction = None
        elif direction == last_direction:
            streak = streak + 1 if streak > 0 else streak - 1
            if direction == "up":
                streak = abs(streak)
            else:
                streak = -abs(streak)
        else:
            streak = 1 if direction == "up" else -1
            last_direction = direction

        result.append(streak)

    return pd.Series(result, index=gap_series.index)


def build_gap_database(daily_df: pd.DataFrame, intraday_df: Optional[pd.DataFrame] = None,
                       vix_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Main builder: takes raw daily OHLCV and produces complete gap statistics for all sessions.
    Handles holiday exclusion, data quality, and all computed fields.
    """
    if daily_df is None or len(daily_df) < 2:
        logger.error("Insufficient daily data for gap database")
        return pd.DataFrame()

    # Ensure sorted by date
    daily_df = daily_df.sort_values("date").reset_index(drop=True)

    # Data quality filter
    daily_df["session_range_pct"] = (daily_df["high"] - daily_df["low"]) / daily_df["open"].abs()
    daily_df["excluded"] = (
        (daily_df["volume"] == 0) |
        (daily_df["session_range_pct"] > MAX_SESSION_MOVE_PCT) |
        (daily_df["close"] == 0)
    )

    # Exclude known holidays
    daily_df["is_holiday"] = daily_df["date"].apply(
        lambda d: is_market_holiday(datetime.strptime(str(d), "%Y-%m-%d").date())
    )
    daily_df.loc[daily_df["is_holiday"], "excluded"] = True

    # Build intraday lookup by date
    intraday_by_date = {}
    if intraday_df is not None and len(intraday_df) > 0:
        for grp_date, grp in intraday_df.groupby("date"):
            intraday_by_date[str(grp_date)] = grp.sort_values("bar_index").reset_index(drop=True)

    # Build VIX lookup by date
    vix_by_date = {}
    if vix_df is not None and len(vix_df) > 0:
        for _, row in vix_df.iterrows():
            vix_by_date[str(row["date"])] = float(row["close"])

    records = []
    valid_closes = daily_df[~daily_df["excluded"]]["close"].tolist()
    closes_arr = pd.Series(valid_closes)

    for i in range(1, len(daily_df)):
        row = daily_df.iloc[i]
        date_str = str(row["date"])

        if row.get("excluded") or row.get("is_holiday"):
            continue

        # Find prior valid session (skip excluded sessions)
        prior_idx = i - 1
        while prior_idx >= 0 and (daily_df.iloc[prior_idx].get("excluded") or
                                    daily_df.iloc[prior_idx].get("is_holiday")):
            prior_idx -= 1

        if prior_idx < 0:
            continue

        prior_row = daily_df.iloc[prior_idx]
        prior_date_str = str(prior_row["date"])

        # Holiday gap exclusion: don't compute gaps across holidays
        current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        prior_date = datetime.strptime(prior_date_str, "%Y-%m-%d").date()
        business_days_apart = 0
        check = prior_date + timedelta(days=1)
        while check <= current_date:
            if check.weekday() < 5 and not is_market_holiday(check):
                business_days_apart += 1
            check += timedelta(days=1)

        if business_days_apart > 1:
            # Holiday gap — exclude
            continue

        # Calendar flags
        cal = get_calendar_flags(current_date)

        # VIX
        vix_prior = vix_by_date.get(prior_date_str)
        vix_current = vix_by_date.get(date_str)

        # Trend regime using trailing closes
        row_idx_in_valid = len(records)  # approximate
        if len(records) >= 200:
            recent_closes = pd.Series([r["close"] for r in records[-200:]])
            regime = compute_sma_regime(recent_closes)
        else:
            regime = "insufficient_data"

        # Prior day type
        prior_day_type = classify_day_type(prior_row)

        # Gap stats
        intraday = intraday_by_date.get(date_str)
        gap_stats = compute_gap_stats_for_session(row, prior_row, intraday)

        record = {
            "date": date_str,
            "day_of_week": cal["day_of_week"],
            "month": cal["month"],
            "week_of_month": cal["week_of_month"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row.get("volume", 0) or 0),
            "prior_close": float(prior_row["close"]),
            "prior_high": float(prior_row["high"]),
            "prior_low": float(prior_row["low"]),
            "prior_open": float(prior_row["open"]),
            "vix_prior_close": vix_prior,
            "vix_current": vix_current,
            "trend_regime": regime,
            "prior_day_type": prior_day_type,
            "is_fomc_day": cal["is_fomc_day"],
            "is_fomc_eve": cal["is_fomc_eve"],
            "is_opex_friday": cal["is_opex_friday"],
            "is_quarter_end": cal["is_quarter_end"],
            "is_expiry_week": cal["is_expiry_week"],
            "has_intraday": intraday is not None,
            **gap_stats,
        }
        records.append(record)

    df_out = pd.DataFrame(records)

    # Add consecutive gap streak
    if "gap_direction" in df_out.columns:
        df_out["consecutive_gap_streak"] = compute_consecutive_gap_streak(df_out["gap_direction"])

    logger.info(f"Gap database built: {len(df_out)} valid sessions")
    return df_out
