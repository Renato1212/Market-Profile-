package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelStatus;

import java.util.ArrayList;
import java.util.List;

/**
 * Scans bar arrays from each level's emission bar to the current bar,
 * marks touches and breaks, applies touch-count attenuation, and drops
 * BROKEN levels.
 *
 * Pure Java — no SDK imports.
 */
public final class StatusUpdater {

    /**
     * Touch-attenuation factor.
     * Each additional touch multiplies strength by 1 / (1 + ATTENUATION * touchCount).
     */
    private static final double TOUCH_ATTENUATION = 0.3;

    /**
     * Minimum bar gap between two recognised touches of the same level.
     * Prevents a multi-bar consolidation from being counted as many touches.
     */
    private static final int MIN_TOUCH_GAP = 3;

    /**
     * Fraction of ATR that the bar body must extend beyond the level zone
     * before the level is considered broken.
     */
    private static final double BREAK_ATR_FRACTION = 0.5;

    /**
     * Walks bar data from each level's emission bar to {@code currentBar},
     * tracking touches and breaks.  Returns the surviving (non-BROKEN) levels
     * with updated strength, status and touch count.
     *
     * @param levels     input levels (may be empty)
     * @param highs      bar highs indexed 0..N-1
     * @param lows       bar lows
     * @param opens      bar opens
     * @param closes     bar closes
     * @param currentBar uppermost bar index to inspect (must be < array lengths)
     * @param atr        current ATR value for break detection
     * @return surviving levels
     */
    public static List<Level> markTouchesAndBreaks(
            List<Level> levels,
            double[] highs, double[] lows, double[] opens, double[] closes,
            int currentBar, double atr) {

        if (levels.isEmpty()) return new ArrayList<>();

        List<Level> result = new ArrayList<>(levels.size());
        for (Level level : levels) {
            Level updated = processLevel(level, highs, lows, opens, closes,
                    currentBar, atr);
            if (updated.status != LevelStatus.BROKEN) {
                result.add(updated);
            }
        }
        return result;
    }

    // ------------------------------------------------------------------ private

    private static Level processLevel(Level level,
                                      double[] highs, double[] lows,
                                      double[] opens, double[] closes,
                                      int currentBar, double atr) {
        int  touches     = level.touchCount;
        LevelStatus status = level.status;
        int  lastTouchBar  = -1;
        boolean broken     = false;

        int scanStart = level.barIndex + 1;
        int scanEnd   = Math.min(currentBar, highs.length - 1);

        for (int i = scanStart; i <= scanEnd; i++) {
            double barHigh  = highs[i];
            double barLow   = lows[i];
            double barOpen  = opens[i];
            double barClose = closes[i];

            // --- Touch detection ------------------------------------------
            // A bar "touches" the level zone when any part of its range overlaps.
            boolean priceOverlap = barHigh >= level.priceLow && barLow <= level.priceHigh;
            if (priceOverlap) {
                boolean gapOk = (lastTouchBar < 0 || (i - lastTouchBar) >= MIN_TOUCH_GAP);
                if (gapOk) {
                    touches++;
                    lastTouchBar = i;
                    status = LevelStatus.TESTED;
                }
            }

            // --- Break detection ------------------------------------------
            // A break requires the bar body (open↔close) to be fully outside
            // the zone AND the displacement from the level mid to be > 0.5 ATR.
            double bodyHigh = Math.max(barOpen, barClose);
            double bodyLow  = Math.min(barOpen, barClose);
            boolean bodyAbove = bodyLow  > level.priceHigh;
            boolean bodyBelow = bodyHigh < level.priceLow;

            if (bodyAbove || bodyBelow) {
                double displacement = Math.abs(
                        (bodyAbove ? bodyLow : bodyHigh) - level.midPrice());
                if (displacement > BREAK_ATR_FRACTION * atr) {
                    status = LevelStatus.BROKEN;
                    broken = true;
                    break;
                }
            }
        }

        if (broken) {
            // Return a BROKEN level so the caller can drop it
            return level.withStatus(LevelStatus.BROKEN);
        }

        // Apply touch attenuation:  strength *= 1 / (1 + 0.3 * touches)
        double attenuated = level.rawStrength * (1.0 / (1.0 + TOUCH_ATTENUATION * touches));
        Level withAttenuation = TimeDecay.levelWithStrength(level, attenuated);
        return withAttenuation.withStatus(status).withTouchCount(touches);
    }

    private StatusUpdater() {}
}
