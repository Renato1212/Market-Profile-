"""
ATLAS AI Trading Copilot — Pillar 4.
Powered by Anthropic Claude API.

HALLUCINATION GUARD: Atlas NEVER invents statistics.
All numbers passed via structured context dict → inserted verbatim into prompt.
Claude only interprets and synthesizes — never generates raw statistics.

Cost management:
- Pre-market plan: claude-opus-4-7 (once/day/user, cached)
- Live alerts: claude-haiku-4-5 (max 1 per 5-min window)
- Ad-hoc queries: claude-haiku-4-5 (response < 300 tokens)
"""
import json
from datetime import datetime
from typing import Optional
import logging
import anthropic

logger = logging.getLogger(__name__)

ATLAS_SYSTEM_PROMPT = """You are ATLAS, an institutional-grade ES Futures intraday trading copilot.
You synthesize quantitative data into actionable trading intelligence using:
- Jim Dalton's auction market theory (Mind Over Markets)
- Pete Steidlmayer's Market Profile
- Axia Futures order flow methodology
- Modern dealer gamma exposure modeling

Your rules:
1. NEVER invent or estimate statistics. Only cite numbers from the data context provided to you.
2. NEVER say "go long" or "go short" — only provide context, scenarios, and probabilities.
3. ALWAYS state probabilities with their sample size (N=).
4. Frame the day's likely structure: trend, rotational, or double distribution.
5. Identify inflection levels and what they mean for auction theory.
6. Flag risk events and regime shifts as they develop.
7. Write in clear, professional language. No unnecessary filler text.
8. Think in scenarios and probabilities, not certainties.
9. When data is absent or marked N/A, acknowledge it — do not fill gaps with assumptions.
10. You are an educational and analytical tool, not a financial advisor."""


async def generate_premarket_briefing(context: dict, api_key: str) -> dict:
    """
    Generate the daily pre-market briefing using claude-opus-4-7.
    Context dict must contain all real computed data — no hallucination possible.
    Returns formatted briefing text + metadata.
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = _build_premarket_prompt(context)

    try:
        response = await client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            system=ATLAS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return {
            "content": content,
            "model": "claude-opus-4-7",
            "tokens_used": tokens,
            "generated_at": datetime.utcnow().isoformat(),
            "success": True,
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error for pre-market briefing: {e}")
        return {"success": False, "error": str(e), "content": _fallback_briefing(context)}


async def generate_live_alert(alert_type: str, trigger_data: dict, api_key: str) -> dict:
    """
    Generate a live intraday alert using claude-haiku-4-5.
    Fast, cheap, cached 5-min window.
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = _build_alert_prompt(alert_type, trigger_data)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=350,
            system=ATLAS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return {
            "content": content,
            "alert_type": alert_type,
            "model": "claude-haiku-4-5",
            "tokens_used": tokens,
            "generated_at": datetime.utcnow().isoformat(),
            "success": True,
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API alert error: {e}")
        return {"success": False, "error": str(e), "content": None}


async def chat_query(question: str, context: dict, api_key: str, conversation_history: list = None) -> dict:
    """
    Ad-hoc chat interface for trader queries.
    Uses claude-haiku-4-5 with context injection.
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    messages = []
    if conversation_history:
        messages.extend(conversation_history[-6:])  # Last 3 exchanges

    messages.append({
        "role": "user",
        "content": f"""Current market context:
{json.dumps(context, indent=2, default=str)}

Trader question: {question}

Answer using ONLY the data provided above. Cite specific numbers and sample sizes."""
    })

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=500,
            system=ATLAS_SYSTEM_PROMPT,
            messages=messages,
        )

        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return {
            "content": content,
            "model": "claude-haiku-4-5",
            "tokens_used": tokens,
            "success": True,
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic chat error: {e}")
        return {"success": False, "error": str(e), "content": "Data unavailable. Please try again."}


def _build_premarket_prompt(ctx: dict) -> str:
    """Build structured pre-market prompt from context data."""
    date_str = ctx.get("date", datetime.now().strftime("%Y-%m-%d"))
    day_name = ctx.get("day_name", "")

    es = ctx.get("es", {})
    gap = ctx.get("gap", {})
    vix = ctx.get("vix", {})
    macro = ctx.get("macro", {})
    gex = ctx.get("gex", {})
    levels = ctx.get("key_levels", {})
    calendar = ctx.get("calendar", {})
    cot = ctx.get("cot", {})
    crypto = ctx.get("crypto", {})
    dxy = ctx.get("dxy", {})
    a_period_hist = ctx.get("a_period_historical", {})

    return f"""Generate the ATLAS pre-market intelligence briefing for {date_str} ({day_name}).

=== MARKET DATA (use these exact numbers — do not estimate) ===

ES FUTURES:
- Current price: {es.get('current_price', 'N/A')}
- Prior cash close: {levels.get('prior_close', 'N/A')}
- Overnight high: {es.get('overnight_high', 'N/A')}
- Overnight low: {es.get('overnight_low', 'N/A')}
- Overnight range: {es.get('overnight_range', 'N/A')} pts

GAP STATUS:
- Direction: {gap.get('direction', 'N/A')}
- Size: {gap.get('size_pts', 'N/A')} pts ({gap.get('size_pct', 'N/A')}%)
- Historical same-session fill rate (matching context): {gap.get('fill_probability_pct', 'N/A')}% (N={gap.get('sample_size', 'N/A')})
- Confidence: {gap.get('confidence', 'N/A')}
- Median fill time: {gap.get('median_fill_time', 'N/A')} minutes
- Size bucket: {gap.get('size_bucket', 'N/A')}
- Opening context: {gap.get('gap_context', 'N/A')}

KEY LEVELS (ES):
- Prior Cash Close: {levels.get('prior_close', 'N/A')}
- Prior Day High: {levels.get('pdh', 'N/A')}
- Prior Day Low: {levels.get('pdl', 'N/A')}
- Value Area High (VAH): {levels.get('vah', 'N/A')}
- Point of Control (POC): {levels.get('poc', 'N/A')}
- Value Area Low (VAL): {levels.get('val', 'N/A')}
- Call Wall (ES equivalent): {gex.get('call_wall_es', 'N/A')}
- Put Wall (ES equivalent): {gex.get('put_wall_es', 'N/A')}
- Zero Gamma Flip (ES equivalent): {gex.get('zero_gamma_es', 'N/A')}
- Overnight High: {es.get('overnight_high', 'N/A')}
- Overnight Low: {es.get('overnight_low', 'N/A')}

DEALER POSITIONING:
- GEX Regime: {gex.get('regime', 'N/A').upper() if gex.get('regime') else 'N/A'} GAMMA
- Net GEX: {gex.get('net_gex', 'N/A')} billion
- Regime description: {gex.get('regime_detail', {}).get('description', 'N/A')}

VIX ENVIRONMENT:
- VIX: {vix.get('vix', {}).get('current', 'N/A')} (change: {vix.get('vix', {}).get('change', 'N/A')})
- VIX9D: {vix.get('vix9d', {}).get('current', 'N/A')}
- VIX3M: {vix.get('vix3m', {}).get('current', 'N/A')}
- Term structure: {'Backwardation (STRESS)' if vix.get('term_structure', {}).get('backwardation') else 'Contango (calm)'}

MACRO:
- 10Y Yield: {macro.get('yield_10y', {}).get('value', 'N/A')}% (change: {macro.get('yield_10y', {}).get('change', 'N/A')})
- 2Y Yield: {macro.get('yield_2y', {}).get('value', 'N/A')}%
- Yield Curve: {macro.get('yield_curve', {}).get('spread', 'N/A')}% ({'INVERTED' if macro.get('yield_curve', {}).get('inverted') else 'normal'})
- DXY: {dxy.get('current', 'N/A')} (change: {dxy.get('change_pct', 'N/A')}%)
- BTC overnight: {crypto.get('btc', {}).get('change_pct', 'N/A')}% ({crypto.get('btc', {}).get('risk_signal', 'N/A')})

POSITIONING:
- Large Spec COT (ES futures): {cot.get('large_spec_net', 'N/A')} contracts net ({cot.get('bias', 'N/A')})
- COT weekly change: {cot.get('weekly_change', 'N/A')}
- COT 52-week percentile: {cot.get('percentile_52w', 'N/A')}%

CALENDAR:
- FOMC Day: {calendar.get('is_fomc_day', False)}
- FOMC Eve: {calendar.get('is_fomc_eve', False)}
- OPEX Friday: {calendar.get('is_opex_friday', False)}
- Quarter End: {calendar.get('is_quarter_end', False)}
- Today's high-impact events: {json.dumps(calendar.get('events', []))}

=== OUTPUT FORMAT ===

Produce the ATLAS pre-market briefing in exactly this format:

═══════════════════════════════════════════════════════════
ATLAS PRE-MARKET INTELLIGENCE — {date_str}
═══════════════════════════════════════════════════════════

▌ MARKET CONTEXT
[2-3 sentences synthesizing overnight action, macro drivers, and regime]

▌ KEY LEVELS (ES)
[List all key levels provided above in clean format]

▌ DEALER POSITIONING REGIME
[LONG/SHORT/NEUTRAL GAMMA] — [plain-English interpretation of what this means for today]

▌ GAP STATUS
[Cite fill probability with N=sample. Context on what similar gaps historically did.]

▌ DAY TYPE EARLY READ
[Based on gap context and overnight structure, what day type is most probable?]

▌ HIGH-IMPACT EVENTS TODAY
[List from calendar data]

▌ TOP 3 SCENARIOS

Scenario A (Probability: XX%): [Name]
- Trigger: [specific price action that confirms this scenario]
- Behavior: [how the session would unfold]
- Key levels: [specific ES levels to watch]
- Risk: [what would invalidate]

Scenario B (Probability: XX%): [Name]
[same format]

Scenario C (Probability: XX%): [Name]
[same format]

▌ POSITIONING CONTEXT
[COT smart money positioning + P/C ratio context]

▌ RISK FACTORS
[Bullet list: what could cause today to behave unexpectedly]

▌ EXECUTION REMINDERS
[3-5 frame-of-mind reminders — NOT trade signals. Professional mindset cues.]"""


def _build_alert_prompt(alert_type: str, data: dict) -> str:
    """Build concise prompt for live alert generation."""
    alert_templates = {
        "level_approach": f"""Generate a LEVEL ALERT for ATLAS.
ES is approaching a key level.
Data: {json.dumps(data, default=str)}
Format: Start with 🔔 LEVEL ALERT. One paragraph, 2-3 sentences.
Cite the specific level, distance, regime context, and historical behavior at this level (use only numbers from data).
End with the fill rate or bounce rate from the data.""",

        "regime_shift": f"""Generate a REGIME SHIFT ALERT for ATLAS.
GEX regime has changed.
Data: {json.dumps(data, default=str)}
Format: Start with ⚡ REGIME SHIFT ALERT. 2-3 sentences.
State the shift direction, what it means for volatility, and cite the specific GEX levels from data.""",

        "a_period_complete": f"""Generate an A PERIOD COMPLETE ALERT for ATLAS.
A Period (09:30-10:00 ET) has just ended.
Data: {json.dumps(data, default=str)}
Format: Start with 🎯 A PERIOD COMPLETE. 3-4 sentences.
State the A Period type, close position, day type probability, and key level implications.
Use ONLY the numbers and probabilities from the data provided.""",

        "gap_update": f"""Generate a GAP UPDATE ALERT for ATLAS.
Gap status update.
Data: {json.dumps(data, default=str)}
Format: Start with 📊 GAP UPDATE. 2 sentences.
State current gap fill status, historical fill rate at this time of day, and MAE context.""",

        "macro_spike": f"""Generate a MACRO ALERT for ATLAS.
Significant macro move detected.
Data: {json.dumps(data, default=str)}
Format: Start with 🌐 MACRO ALERT. 2-3 sentences.
State what moved, magnitude, and what it typically means for ES.""",

        "event_warning": f"""Generate an EVENT WARNING ALERT for ATLAS.
Economic release approaching.
Data: {json.dumps(data, default=str)}
Format: Start with ⚠️ EVENT ALERT. 2 sentences.
State the event name, time, and historical ES range expansion data if provided.""",
    }

    return alert_templates.get(alert_type, f"""Generate a brief ATLAS alert for event type: {alert_type}
Data: {json.dumps(data, default=str)}
Keep it to 2-3 sentences. Cite only data from the provided context.""")


def _fallback_briefing(ctx: dict) -> str:
    """Static fallback when AI is unavailable — pulls data directly."""
    date_str = ctx.get("date", datetime.now().strftime("%Y-%m-%d"))
    gap = ctx.get("gap", {})
    gex = ctx.get("gex", {})
    levels = ctx.get("key_levels", {})

    return f"""ATLAS PRE-MARKET INTELLIGENCE — {date_str}
[AI service temporarily unavailable — data summary only]

KEY LEVELS: VAH={levels.get('vah', 'N/A')} | POC={levels.get('poc', 'N/A')} | VAL={levels.get('val', 'N/A')}
Prior Close: {levels.get('prior_close', 'N/A')} | PDH: {levels.get('pdh', 'N/A')} | PDL: {levels.get('pdl', 'N/A')}

GAP: {gap.get('direction', 'N/A').upper()} {gap.get('size_pts', 'N/A')} pts | Historical fill rate: {gap.get('fill_probability_pct', 'N/A')}%

DEALER REGIME: {gex.get('regime', 'N/A').upper()} GAMMA | Call Wall: {gex.get('call_wall_es', 'N/A')} | Put Wall: {gex.get('put_wall_es', 'N/A')}"""


def check_alert_thresholds(
    current_es: float,
    gex_data: dict,
    a_period_data: dict,
    gap_data: dict,
    vix_data: dict,
    last_alert_times: dict,
    min_alert_interval_seconds: int = 300,
) -> list[dict]:
    """
    Check if any alert thresholds are triggered.
    Rate-limited: max 1 alert per type per 5-min window.
    Returns list of triggered alerts with type + data payload.
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    triggered = []

    def can_alert(alert_type: str) -> bool:
        last = last_alert_times.get(alert_type)
        return last is None or (now - last).total_seconds() > min_alert_interval_seconds

    # Level approach: within 1.5 pts of Call or Put Wall
    call_wall_es = gex_data.get("call_wall_es")
    put_wall_es = gex_data.get("put_wall_es")

    if call_wall_es and abs(current_es - call_wall_es) <= 1.5 and can_alert("level_call_wall"):
        triggered.append({
            "type": "level_approach",
            "subtype": "call_wall",
            "data": {"es_price": current_es, "level": call_wall_es, "distance": round(call_wall_es - current_es, 2),
                     "regime": gex_data.get("regime"), "level_type": "Call Wall (resistance)"},
        })

    if put_wall_es and abs(current_es - put_wall_es) <= 1.5 and can_alert("level_put_wall"):
        triggered.append({
            "type": "level_approach",
            "subtype": "put_wall",
            "data": {"es_price": current_es, "level": put_wall_es, "distance": round(current_es - put_wall_es, 2),
                     "regime": gex_data.get("regime"), "level_type": "Put Wall (support)"},
        })

    # VIX spike: >5% intraday
    vix_change_pct = vix_data.get("vix", {}).get("change_pct", 0)
    if abs(vix_change_pct) > 5 and can_alert("macro_vix"):
        triggered.append({
            "type": "macro_spike",
            "data": {"vix_change_pct": vix_change_pct, "vix_level": vix_data.get("vix", {}).get("current")},
        })

    # A Period complete (10:00 ET)
    if a_period_data.get("just_completed") and can_alert("a_period_complete"):
        triggered.append({
            "type": "a_period_complete",
            "data": a_period_data,
        })

    return triggered
