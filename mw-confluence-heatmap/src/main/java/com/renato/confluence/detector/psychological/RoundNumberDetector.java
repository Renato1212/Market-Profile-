package com.renato.confluence.detector.psychological;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Emits psychological round-number levels in the vicinity of the current price.
 *
 * Four tiers are derived dynamically from the instrument's ATR and tick size:
 *
 *   MAJOR   — largest round interval (1000s for ES, 1.0 for FX majors, etc.)
 *   MEDIUM  — mid-level interval (e.g. 500s, 0.50)
 *   MINOR   — smaller interval (e.g. 100s, 0.10)
 *   SUBMINOR— finest interval (e.g. 50s, 0.05)
 *
 * The intervals are scaled from the ATR so that roughly 2–4 levels of each tier
 * fall within a ±20 ATR window around the current price.
 *
 * Once generated, round-number levels never decay (halfLife = MAX_VALUE).
 * They are regenerated on each bar to track the moving price window.
 */
public final class RoundNumberDetector extends BaseDetector {

    private static final int    WINDOW_ATR_MULTIPLES = 20; // ± 20 ATR window
    private static final double MAJOR_ATR_MULTIPLE   = 10.0;
    private static final double MEDIUM_ATR_MULTIPLE  = 5.0;
    private static final double MINOR_ATR_MULTIPLE   = 2.0;
    private static final double SUBMINOR_ATR_MULTIPLE = 1.0;

    private static final LevelType[] TYPES = {
        LevelType.ROUND_NUMBER_MAJOR,
        LevelType.ROUND_NUMBER_MEDIUM,
        LevelType.ROUND_NUMBER_MINOR,
        LevelType.ROUND_NUMBER_SUBMINOR
    };

    public RoundNumberDetector() {
        super(true);
    }

    public RoundNumberDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int    i        = ctx.getCurrentIndex();
        double close    = ctx.getClose(i);
        double atr      = ctx.getAtr14();
        double tickSize = ctx.getTickSize();
        long   ts       = ctx.getStartTime(i);

        if (atr <= 0 || tickSize <= 0) return;

        // Compute tier intervals, rounded to tick multiples
        double majorInterval    = roundToNiceTick(MAJOR_ATR_MULTIPLE   * atr, tickSize);
        double mediumInterval   = roundToNiceTick(MEDIUM_ATR_MULTIPLE  * atr, tickSize);
        double minorInterval    = roundToNiceTick(MINOR_ATR_MULTIPLE   * atr, tickSize);
        double subminorInterval = roundToNiceTick(SUBMINOR_ATR_MULTIPLE * atr, tickSize);

        double priceMin = close - WINDOW_ATR_MULTIPLES * atr;
        double priceMax = close + WINDOW_ATR_MULTIPLES * atr;

        emitTier(ctx, i, ts, LevelType.ROUND_NUMBER_MAJOR,    majorInterval,    priceMin, priceMax, 1.0);
        emitTier(ctx, i, ts, LevelType.ROUND_NUMBER_MEDIUM,   mediumInterval,   priceMin, priceMax, 0.75);
        emitTier(ctx, i, ts, LevelType.ROUND_NUMBER_MINOR,    minorInterval,    priceMin, priceMax, 0.5);
        emitTier(ctx, i, ts, LevelType.ROUND_NUMBER_SUBMINOR, subminorInterval, priceMin, priceMax, 0.3);
    }

    // ------------------------------------------------------------------ helpers

    private void emitTier(DetectorContext ctx, int barIndex, long ts,
                          LevelType type, double interval,
                          double priceMin, double priceMax, double strength) {
        if (interval <= 0) return;

        // Find the first round number at or above priceMin
        double firstLevel = Math.ceil(priceMin / interval) * interval;

        for (double price = firstLevel; price <= priceMax; price += interval) {
            // Round to avoid floating-point drift
            double rounded = Math.round(price / interval) * interval;

            Map<String, Object> meta = new HashMap<>();
            meta.put("interval", interval);

            emit(new Level(
                    rounded, rounded, strength,
                    type, ts, barIndex, meta));
        }
    }

    /**
     * Rounds {@code rawInterval} to the nearest "nice" multiple of {@code tickSize}.
     * Ensures levels always land on valid tick boundaries.
     * The nice multiple is chosen so the interval >= 2 ticks.
     */
    private static double roundToNiceTick(double rawInterval, double tickSize) {
        long ticks = Math.max(2L, Math.round(rawInterval / tickSize));
        // Round up to a power-of-10 or 5×power-of-10 multiple of ticks for aesthetics
        // For simplicity, just use rounded ticks × tickSize
        return ticks * tickSize;
    }
}
