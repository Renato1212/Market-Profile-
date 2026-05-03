"""
Gap Fill Statistics Tables — produces all master tables and interactive calculator.

Table A: Opening Location Matrix
Table B: Gap Size Buckets
Table C: Cumulative Fill Probability Curve
Interactive Calculator: context-aware fill probability
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

from services.gap_engine.gap_calculator import classify_gap_size

logger = logging.getLogger(__name__)

CONFIDENCE_LEVELS = {
    "low": (0, 30),
    "medium": (30, 100),
    "high": (100, float("inf")),
}


def _confidence_badge(n: int) -> str:
    if n < 10:
        return "insufficient"
    elif n < 30:
        return "low"
    elif n < 100:
        return "medium"
    else:
        return "high"


def _fill_rate_stats(subset: pd.DataFrame) -> dict:
    """Compute fill rate statistics for a filtered subset of gap sessions."""
    gap_rows = subset[subset["gap_direction"].isin(["up", "down"])].copy()
    n = len(gap_rows)

    if n == 0:
        return {"n": 0, "fill_rate_pct": None, "confidence": "insufficient",
                "avg_fill_time": None, "median_fill_time": None, "avg_mae": None,
                "fill_by_1030_pct": None, "fill_by_1200_pct": None,
                "fill_by_1400_pct": None, "no_fill_pct": None}

    filled = gap_rows[gap_rows["filled_same_session"] == True]
    fill_rate = len(filled) / n * 100

    fill_times = filled["fill_time_minutes"].dropna()
    avg_fill_time = float(fill_times.mean()) if len(fill_times) > 0 else None
    median_fill_time = float(fill_times.median()) if len(fill_times) > 0 else None

    maes = filled["mae_before_fill_pts"].dropna()
    avg_mae = float(maes.mean()) if len(maes) > 0 else None

    # Time-bucketed fill rates (only for sessions with intraday data)
    intraday = gap_rows[gap_rows["has_intraday"] == True]
    n_intraday = len(intraday)

    if n_intraday > 0:
        fill_by_1030 = len(intraday[(intraday["filled_same_session"]) & (intraday["fill_time_minutes"] <= 60)]) / n_intraday * 100
        fill_by_1200 = len(intraday[(intraday["filled_same_session"]) & (intraday["fill_time_minutes"] <= 150)]) / n_intraday * 100
        fill_by_1400 = len(intraday[(intraday["filled_same_session"]) & (intraday["fill_time_minutes"] <= 270)]) / n_intraday * 100
    else:
        fill_by_1030 = fill_by_1200 = fill_by_1400 = None

    return {
        "n": n,
        "fill_rate_pct": round(fill_rate, 1),
        "confidence": _confidence_badge(n),
        "avg_fill_time": round(avg_fill_time, 0) if avg_fill_time else None,
        "median_fill_time": round(median_fill_time, 0) if median_fill_time else None,
        "avg_mae": round(avg_mae, 2) if avg_mae else None,
        "fill_by_1030_pct": round(fill_by_1030, 1) if fill_by_1030 is not None else None,
        "fill_by_1200_pct": round(fill_by_1200, 1) if fill_by_1200 is not None else None,
        "fill_by_1400_pct": round(fill_by_1400, 1) if fill_by_1400 is not None else None,
        "no_fill_pct": round(100 - fill_rate, 1),
    }


def build_table_a_opening_location(gap_df: pd.DataFrame) -> list[dict]:
    """
    Table A: Opening Location Matrix
    Rows: gap_context categories
    """
    contexts = [
        "above_vah", "in_value_upper", "at_poc", "in_value_mid",
        "in_value_lower", "below_val", "above_pdh", "below_pdl",
        "inside_prior_range", "outside_prior_range",
    ]

    rows = []
    for ctx in contexts:
        subset = gap_df[gap_df["gap_context"] == ctx]
        if len(subset) == 0:
            subset_up = pd.DataFrame()
            subset_down = pd.DataFrame()
        else:
            subset_up = subset[subset["gap_direction"] == "up"]
            subset_down = subset[subset["gap_direction"] == "down"]

        row = {
            "context": ctx,
            "context_label": ctx.replace("_", " ").title(),
            "all": _fill_rate_stats(subset),
            "gap_up": _fill_rate_stats(subset_up),
            "gap_down": _fill_rate_stats(subset_down),
        }
        rows.append(row)

    return rows


def build_table_b_gap_size(gap_df: pd.DataFrame) -> list[dict]:
    """
    Table B: Gap Size Buckets
    Rows: size × direction combinations
    """
    sizes = ["micro", "small", "medium", "large", "extreme"]
    directions = ["up", "down"]
    rows = []

    for size in sizes:
        for direction in directions:
            subset = gap_df[
                (gap_df["gap_direction"] == direction) &
                (gap_df["gap_size_pts"].apply(
                    lambda x: classify_gap_size(x) == size if pd.notna(x) else False
                ))
            ]
            stats = _fill_rate_stats(subset)

            size_ranges = {
                "micro": "0.25–3 pts",
                "small": "3–8 pts",
                "medium": "8–20 pts",
                "large": "20–40 pts",
                "extreme": "40+ pts",
            }

            rows.append({
                "size": size,
                "size_label": f"{size.title()} ({size_ranges[size]})",
                "direction": direction,
                **stats,
            })

    return rows


def build_table_c_cumulative_curve(gap_df: pd.DataFrame) -> dict:
    """
    Table C: Cumulative Fill Probability Curve
    For each minute 0-390 from 09:30, what % of gaps have filled?
    """
    filled_intraday = gap_df[
        (gap_df["filled_same_session"] == True) &
        (gap_df["has_intraday"] == True) &
        (gap_df["fill_time_minutes"].notna())
    ].copy()

    total_gap_sessions_with_intraday = len(gap_df[
        (gap_df["gap_direction"].isin(["up", "down"])) &
        (gap_df["has_intraday"] == True)
    ])

    if total_gap_sessions_with_intraday == 0:
        return {"curve": [], "half_life_minutes": None}

    # Build cumulative curve at 5-minute intervals
    curve = []
    for minute in range(5, 395, 5):
        filled_by_minute = len(filled_intraday[filled_intraday["fill_time_minutes"] <= minute])
        cum_pct = filled_by_minute / total_gap_sessions_with_intraday * 100
        curve.append({"minutes": minute, "cumulative_fill_pct": round(cum_pct, 2)})

    # Half-life: time at which 50% of gaps have filled
    half_life = None
    for pt in curve:
        if pt["cumulative_fill_pct"] >= 50:
            half_life = pt["minutes"]
            break

    # Same for gap up vs gap down
    curve_up = []
    curve_down = []
    for direction, curve_list in [("up", curve_up), ("down", curve_down)]:
        dir_filled = filled_intraday[
            gap_df.loc[filled_intraday.index, "gap_direction"] == direction
        ] if len(filled_intraday) > 0 else pd.DataFrame()
        dir_total = len(gap_df[
            (gap_df["gap_direction"] == direction) &
            (gap_df["has_intraday"] == True)
        ])
        if dir_total > 0:
            for minute in range(5, 395, 5):
                if len(dir_filled) > 0:
                    filled_by = len(dir_filled[dir_filled["fill_time_minutes"] <= minute])
                    cum = filled_by / dir_total * 100
                else:
                    cum = 0
                curve_list.append({"minutes": minute, "cumulative_fill_pct": round(cum, 2)})

    return {
        "curve": curve,
        "curve_up": curve_up,
        "curve_down": curve_down,
        "half_life_minutes": half_life,
        "total_sessions": total_gap_sessions_with_intraday,
    }


def compute_fill_probability(
    gap_df: pd.DataFrame,
    gap_direction: str,
    gap_size_pts: float,
    day_of_week: Optional[int] = None,
    vix_level: Optional[float] = None,
    trend_regime: Optional[str] = None,
    prior_day_type: Optional[str] = None,
    is_fomc: bool = False,
    gap_context: Optional[str] = None,
) -> dict:
    """
    Interactive probability calculator.
    Applies available filters and returns fill probability with sample size.
    Confidence degrades gracefully as filters narrow sample.
    """
    base = gap_df[gap_df["gap_direction"] == gap_direction].copy()

    # Apply size bucket filter
    size_bucket = classify_gap_size(gap_size_pts)
    filtered = base[base["gap_size_pts"].apply(
        lambda x: classify_gap_size(x) == size_bucket if pd.notna(x) else False
    )]

    applied_filters = [f"direction={gap_direction}", f"size={size_bucket}"]
    full_stats = _fill_rate_stats(filtered)

    # Progressively add context filters if they improve confidence
    def add_filter(df: pd.DataFrame, col: str, val, label: str):
        subset = df[df[col] == val] if val is not None else df
        if len(subset) >= 10:
            return subset, label
        return df, None

    if gap_context:
        filtered, lbl = add_filter(filtered, "gap_context", gap_context, f"context={gap_context}")
        if lbl:
            applied_filters.append(lbl)

    if day_of_week is not None:
        filtered, lbl = add_filter(filtered, "day_of_week", day_of_week, f"dow={day_of_week}")
        if lbl:
            applied_filters.append(lbl)

    if trend_regime:
        filtered, lbl = add_filter(filtered, "trend_regime", trend_regime, f"regime={trend_regime}")
        if lbl:
            applied_filters.append(lbl)

    if prior_day_type:
        filtered, lbl = add_filter(filtered, "prior_day_type", prior_day_type, f"prior_type={prior_day_type}")
        if lbl:
            applied_filters.append(lbl)

    if is_fomc:
        filtered, lbl = add_filter(filtered, "is_fomc_day", True, "fomc_day")
        if lbl:
            applied_filters.append(lbl)

    # VIX regime filter: bucket VIX into low/mid/high
    if vix_level is not None:
        vix_bucket = "low" if vix_level < 15 else ("high" if vix_level > 25 else "mid")
        vix_filtered = filtered.copy()
        if vix_bucket == "low":
            vix_filtered = filtered[filtered["vix_prior_close"] < 15]
        elif vix_bucket == "high":
            vix_filtered = filtered[filtered["vix_prior_close"] > 25]
        else:
            vix_filtered = filtered[(filtered["vix_prior_close"] >= 15) & (filtered["vix_prior_close"] <= 25)]

        if len(vix_filtered) >= 10:
            filtered = vix_filtered
            applied_filters.append(f"vix={vix_bucket}(<15/{15}-25/>25)")

    final_stats = _fill_rate_stats(filtered)

    # Edge score: 0-100 based on fill rate deviation from base rate and confidence
    base_rate = full_stats["fill_rate_pct"] or 50
    final_rate = final_stats["fill_rate_pct"] or 50
    deviation = abs(final_rate - base_rate)
    conf_multiplier = {"insufficient": 0, "low": 0.3, "medium": 0.7, "high": 1.0}
    edge_score = min(100, int(deviation * conf_multiplier.get(final_stats["confidence"], 0)))

    return {
        "fill_probability_pct": final_stats["fill_rate_pct"],
        "sample_size": final_stats["n"],
        "confidence": final_stats["confidence"],
        "median_fill_time_minutes": final_stats["median_fill_time"],
        "avg_mae_pts": final_stats["avg_mae"],
        "edge_score": edge_score,
        "applied_filters": applied_filters,
        "base_rate_pct": full_stats["fill_rate_pct"],
        "base_n": full_stats["n"],
        "fill_by_1030_pct": final_stats["fill_by_1030_pct"],
        "fill_by_1200_pct": final_stats["fill_by_1200_pct"],
        "fill_by_1400_pct": final_stats["fill_by_1400_pct"],
    }


def run_hypothesis_tests(gap_df: pd.DataFrame) -> list[dict]:
    """
    Hypothesis Testing Panel — test Dalton's claims empirically.
    Returns verdict for each hypothesis with statistical backing.
    """
    from scipy import stats

    tests = []

    # H1: A Period upper third close → session up close >60% of time
    def h1():
        if "a_close_position" not in gap_df.columns or "close" not in gap_df.columns:
            return {"status": "no_data"}
        upper_third = gap_df[(gap_df["a_close_position"].notna()) & (gap_df["a_close_position"] > 66.7)]
        if len(upper_third) < 10:
            return {"n": len(upper_third), "status": "insufficient"}
        up_close = upper_third[upper_third["close"] > upper_third["open"]]
        rate = len(up_close) / len(upper_third) * 100
        p_val = stats.binomtest(len(up_close), len(upper_third), 0.60, alternative="greater").pvalue
        return {"rate": round(rate, 1), "n": len(upper_third), "threshold": 60}

    # H2: Open-Drive vs Open-Auction → trend day rate comparison
    def h2():
        if "a_type" not in gap_df.columns or "day_type" not in gap_df.columns:
            return {"status": "no_data"}
        drive = gap_df[gap_df["a_type"] == "open_drive"]
        auction = gap_df[gap_df["a_type"] == "open_auction"]
        if len(drive) < 10 or len(auction) < 10:
            return {"n_drive": len(drive), "n_auction": len(auction), "status": "insufficient"}
        drive_trend = drive[drive["day_type"].str.contains("trend", na=False)]
        auction_trend = auction[auction["day_type"].str.contains("trend", na=False)]
        rate_drive = len(drive_trend) / len(drive) * 100
        rate_auction = len(auction_trend) / len(auction) * 100
        return {"rate_drive": round(rate_drive, 1), "rate_auction": round(rate_auction, 1),
                "n_drive": len(drive), "n_auction": len(auction)}

    # H3: Open above VAH + bullish A close → gap fill <40%
    def h3():
        if "gap_context" not in gap_df.columns or "a_direction" not in gap_df.columns:
            return {"status": "no_data"}
        subset = gap_df[
            (gap_df["gap_context"] == "above_vah") &
            (gap_df["a_direction"] == "bullish") &
            (gap_df["gap_direction"] == "up")
        ]
        if len(subset) < 10:
            return {"n": len(subset), "status": "insufficient"}
        fill_rate = subset["filled_same_session"].mean() * 100
        return {"fill_rate": round(fill_rate, 1), "n": len(subset), "threshold": 40}

    # H4: Narrow A Period → wider session range
    def h4():
        if "a_range" not in gap_df.columns:
            return {"status": "no_data"}
        valid = gap_df[gap_df["a_range"].notna()].copy()
        if len(valid) < 20:
            return {"status": "insufficient"}
        a_range_20th = valid["a_range"].quantile(0.20)
        narrow = valid[valid["a_range"] <= a_range_20th]
        normal = valid[valid["a_range"] > a_range_20th]
        narrow_range = (narrow["high"] - narrow["low"]).mean()
        normal_range = (normal["high"] - normal["low"]).mean()
        return {"narrow_avg_session_range": round(narrow_range, 2),
                "normal_avg_session_range": round(normal_range, 2),
                "n_narrow": len(narrow), "n_normal": len(normal),
                "ratio": round(narrow_range / normal_range, 2) if normal_range > 0 else None}

    # H5: A Period high in first 5-min bar holds as session high <20% of time
    def h5():
        if "a_high_held_eod" not in gap_df.columns:
            return {"status": "no_data"}
        valid = gap_df[gap_df["a_high_held_eod"].notna()]
        if len(valid) < 10:
            return {"n": len(valid), "status": "insufficient"}
        held_rate = valid["a_high_held_eod"].mean() * 100
        return {"held_rate": round(held_rate, 1), "n": len(valid), "threshold": 20}

    hypothesis_defs = [
        {
            "id": "H1",
            "claim": "A Period closing in upper third predicts session up close >60% of time",
            "fn": h1,
            "pass_condition": lambda r: r.get("rate", 0) > 60 and r.get("n", 0) >= 30,
        },
        {
            "id": "H2",
            "claim": "Open-Drive A Periods produce trend days at higher rates than Open-Auction",
            "fn": h2,
            "pass_condition": lambda r: r.get("rate_drive", 0) > r.get("rate_auction", 0),
        },
        {
            "id": "H3",
            "claim": "Open above VAH + bullish A close → gap fill <40% same session",
            "fn": h3,
            "pass_condition": lambda r: r.get("fill_rate", 100) < 40 and r.get("n", 0) >= 10,
        },
        {
            "id": "H4",
            "claim": "Narrow A Period (< 20th pctile) → wider session range than normal",
            "fn": h4,
            "pass_condition": lambda r: (r.get("ratio", 0) or 0) > 1.05,
        },
        {
            "id": "H5",
            "claim": "A Period high in first 5-min bar holds as session high <20% of time",
            "fn": h5,
            "pass_condition": lambda r: r.get("held_rate", 100) < 20 and r.get("n", 0) >= 30,
        },
    ]

    for hdef in hypothesis_defs:
        try:
            result = hdef["fn"]()
            status = result.get("status", "ok")

            if status == "no_data":
                verdict = "no_data"
                badge = "🔵"
            elif status == "insufficient":
                verdict = "insufficient"
                badge = "🔵"
            elif hdef["pass_condition"](result):
                verdict = "confirmed"
                badge = "✅"
            else:
                verdict = "rejected"
                badge = "❌"

            tests.append({
                "id": hdef["id"],
                "claim": hdef["claim"],
                "result": result,
                "verdict": verdict,
                "badge": badge,
            })
        except Exception as e:
            tests.append({
                "id": hdef["id"],
                "claim": hdef["claim"],
                "result": {"error": str(e)},
                "verdict": "error",
                "badge": "🔵",
            })

    return tests
