package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.HashMap;
import java.util.Map;

/**
 * Detects liquidity sweeps of recent swing highs and lows.
 *
 * A sweep occurs when price briefly trades through a swing extreme but closes
 * on the other side — indicating engineered stop runs followed by reversal.
 *
 * Bull Sweep (SWEEP_LOW):
 *   bar.low < recent swing_low AND bar.close > swing_low
 *   → Price took out sell-stops below the swing and reversed bullishly.
 *
 * Bear Sweep (SWEEP_HIGH):
 *   bar.high > recent swing_high AND bar.close < swing_high
 *   → Price took out buy-stops above the swing and reversed bearishly.
 *
 * Swing detection: N=5 fractal looking back up to LOOKBACK bars.
 *
 * Strength: ((swept distance) / ATR) × log(1 + volume) × ((recovery) / ATR)
 */
public final class SweepDetector extends BaseDetector {

    private static final int    FRACTAL_N   = 5;
    private static final int    LOOKBACK    = 30;
    private static final LevelType[] TYPES  = {
        LevelType.SWEEP_LOW,
        LevelType.SWEEP_HIGH
    };

    public SweepDetector() {
        super(true);
    }

    public SweepDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();
        if (i < FRACTAL_N + 1) return;

        double barHigh  = ctx.getHigh(i);
        double barLow   = ctx.getLow(i);
        double barClose = ctx.getClose(i);
        double atr      = ctx.getAtr14();
        double volume   = ctx.getVolume(i);

        if (atr <= 0) return;

        // Scan for the most recent confirmed fractal swing high and low
        int scanFrom = Math.max(0, i - LOOKBACK);
        int scanTo   = i - FRACTAL_N - 1;   // must have N bars of right-side confirmation

        double recentSwingHigh = Double.NaN;
        double recentSwingLow  = Double.NaN;
        int    swingHighBar    = -1;
        int    swingLowBar     = -1;

        for (int j = scanTo; j >= scanFrom; j--) {
            if (swingHighBar < 0 && isLocalHigh(ctx, j, FRACTAL_N)) {
                recentSwingHigh = ctx.getHigh(j);
                swingHighBar    = j;
            }
            if (swingLowBar < 0 && isLocalLow(ctx, j, FRACTAL_N)) {
                recentSwingLow = ctx.getLow(j);
                swingLowBar    = j;
            }
            if (swingHighBar >= 0 && swingLowBar >= 0) break;
        }

        // ---- Bull sweep -------------------------------------------------------
        if (!Double.isNaN(recentSwingLow) && barLow < recentSwingLow && barClose > recentSwingLow) {
            double swept    = recentSwingLow - barLow;           // distance below swing
            double recovery = barClose - recentSwingLow;         // recovery above swing
            double strength = (swept / atr) * Math.log1p(volume) * (recovery / atr);

            Map<String, Object> meta = new HashMap<>();
            meta.put("swingLow", recentSwingLow);
            meta.put("swingLowBar", swingLowBar);
            meta.put("swept", swept);
            meta.put("recovery", recovery);

            emit(new Level(
                    barLow, recentSwingLow, strength,
                    LevelType.SWEEP_LOW,
                    ctx.getStartTime(i), i,
                    meta));
        }

        // ---- Bear sweep -------------------------------------------------------
        if (!Double.isNaN(recentSwingHigh) && barHigh > recentSwingHigh && barClose < recentSwingHigh) {
            double swept    = barHigh - recentSwingHigh;         // distance above swing
            double recovery = recentSwingHigh - barClose;        // recovery below swing
            double strength = (swept / atr) * Math.log1p(volume) * (recovery / atr);

            Map<String, Object> meta = new HashMap<>();
            meta.put("swingHigh", recentSwingHigh);
            meta.put("swingHighBar", swingHighBar);
            meta.put("swept", swept);
            meta.put("recovery", recovery);

            emit(new Level(
                    recentSwingHigh, barHigh, strength,
                    LevelType.SWEEP_HIGH,
                    ctx.getStartTime(i), i,
                    meta));
        }
    }

    // ------------------------------------------------------------------ helpers

    private boolean isLocalHigh(DetectorContext ctx, int pivotBar, int n) {
        int maxIdx   = ctx.getCurrentIndex();
        double pivot = ctx.getHigh(pivotBar);
        for (int j = 1; j <= n; j++) {
            if (pivotBar - j < 0 || pivotBar + j > maxIdx) return false;
            if (ctx.getHigh(pivotBar - j) >= pivot) return false;
            if (ctx.getHigh(pivotBar + j) >= pivot) return false;
        }
        return true;
    }

    private boolean isLocalLow(DetectorContext ctx, int pivotBar, int n) {
        int maxIdx   = ctx.getCurrentIndex();
        double pivot = ctx.getLow(pivotBar);
        for (int j = 1; j <= n; j++) {
            if (pivotBar - j < 0 || pivotBar + j > maxIdx) return false;
            if (ctx.getLow(pivotBar - j) <= pivot) return false;
            if (ctx.getLow(pivotBar + j) <= pivot) return false;
        }
        return true;
    }
}
