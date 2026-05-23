package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.HashMap;
import java.util.Map;

/**
 * Detects divergences between price swing extremes and the Cumulative Volume Delta (CVD).
 *
 * Bullish divergence:  price makes a new lower low, but CVD makes a higher low.
 *   → Sellers are losing conviction even as price falls.
 *   → Emits CVD_DIVERGENCE_BULL at the new price low.
 *
 * Bearish divergence:  price makes a new higher high, but CVD makes a lower high.
 *   → Buyers are losing conviction even as price rises.
 *   → Emits CVD_DIVERGENCE_BEAR at the new price high.
 *
 * Swing detection: N=5 fractal (price must be lowest/highest among ±5 bars).
 * Strength: |pricePctChange - cvdPctChange| × log(1 + volumeAtSwing)
 */
public final class CVDDivergenceDetector extends BaseDetector {

    private static final int    FRACTAL_N   = 5;
    private static final LevelType[] TYPES  = {
        LevelType.CVD_DIVERGENCE_BULL,
        LevelType.CVD_DIVERGENCE_BEAR
    };

    // Swing state
    private double prevSwingLowPrice  = Double.NaN;
    private double prevSwingLowCvd    = Double.NaN;
    private double prevSwingHighPrice  = Double.NaN;
    private double prevSwingHighCvd   = Double.NaN;

    // CVD accumulator
    private double cumulativeDelta    = 0.0;

    public CVDDivergenceDetector() {
        super(true);
    }

    public CVDDivergenceDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();

        // Update CVD
        cumulativeDelta += ctx.getDelta(i);

        // Need at least FRACTAL_N bars on each side for fractal confirmation
        if (i < FRACTAL_N) return;

        // The fractal pivot is bar (i - FRACTAL_N) — confirmed N bars later
        int pivotBar = i - FRACTAL_N;

        boolean isSwingLow  = isLocalLow(ctx, pivotBar, FRACTAL_N);
        boolean isSwingHigh = isLocalHigh(ctx, pivotBar, FRACTAL_N);

        // CVD at the pivot bar is estimated from running total minus bars added since pivot.
        // We approximate: use current CVD adjusted backwards by N bars' deltas.
        // For exactness, store CVD snapshot at each bar; here we interpolate.
        double cvdAtPivot = estimateCvdAtPivot(ctx, pivotBar, i);
        double volumeAtPivot = ctx.getVolume(pivotBar);

        // ---- Swing low (bullish divergence check) ----------------------------
        if (isSwingLow) {
            double swingLowPrice = ctx.getLow(pivotBar);

            if (!Double.isNaN(prevSwingLowPrice)) {
                boolean lowerLow  = swingLowPrice < prevSwingLowPrice;
                boolean higherCvd = cvdAtPivot    > prevSwingLowCvd;

                if (lowerLow && higherCvd && prevSwingLowPrice != 0) {
                    double pricePct = (swingLowPrice - prevSwingLowPrice) / Math.abs(prevSwingLowPrice);
                    double cvdPct   = prevSwingLowCvd != 0
                            ? (cvdAtPivot - prevSwingLowCvd) / Math.abs(prevSwingLowCvd)
                            : 0.0;
                    double strength = Math.abs(pricePct - cvdPct)
                            * Math.log1p(volumeAtPivot);

                    Map<String, Object> meta = new HashMap<>();
                    meta.put("prevSwingLow", prevSwingLowPrice);
                    meta.put("prevCvd", prevSwingLowCvd);
                    meta.put("cvdAtPivot", cvdAtPivot);

                    emit(new Level(
                            swingLowPrice, swingLowPrice, strength,
                            LevelType.CVD_DIVERGENCE_BULL,
                            ctx.getStartTime(pivotBar), pivotBar,
                            meta));
                }
            }

            prevSwingLowPrice = swingLowPrice;
            prevSwingLowCvd   = cvdAtPivot;
        }

        // ---- Swing high (bearish divergence check) ---------------------------
        if (isSwingHigh) {
            double swingHighPrice = ctx.getHigh(pivotBar);

            if (!Double.isNaN(prevSwingHighPrice)) {
                boolean higherHigh = swingHighPrice > prevSwingHighPrice;
                boolean lowerCvd   = cvdAtPivot     < prevSwingHighCvd;

                if (higherHigh && lowerCvd && prevSwingHighPrice != 0) {
                    double pricePct = (swingHighPrice - prevSwingHighPrice) / Math.abs(prevSwingHighPrice);
                    double cvdPct   = prevSwingHighCvd != 0
                            ? (cvdAtPivot - prevSwingHighCvd) / Math.abs(prevSwingHighCvd)
                            : 0.0;
                    double strength = Math.abs(pricePct - cvdPct)
                            * Math.log1p(volumeAtPivot);

                    Map<String, Object> meta = new HashMap<>();
                    meta.put("prevSwingHigh", prevSwingHighPrice);
                    meta.put("prevCvd", prevSwingHighCvd);
                    meta.put("cvdAtPivot", cvdAtPivot);

                    emit(new Level(
                            swingHighPrice, swingHighPrice, strength,
                            LevelType.CVD_DIVERGENCE_BEAR,
                            ctx.getStartTime(pivotBar), pivotBar,
                            meta));
                }
            }

            prevSwingHighPrice = swingHighPrice;
            prevSwingHighCvd   = cvdAtPivot;
        }
    }

    @Override
    public void reset() {
        super.reset();
        prevSwingLowPrice  = Double.NaN;
        prevSwingLowCvd    = Double.NaN;
        prevSwingHighPrice = Double.NaN;
        prevSwingHighCvd   = Double.NaN;
        cumulativeDelta    = 0.0;
    }

    // ------------------------------------------------------------------ helpers

    private boolean isLocalLow(DetectorContext ctx, int pivotBar, int n) {
        double pivotLow = ctx.getLow(pivotBar);
        int maxIdx = ctx.getCurrentIndex();
        for (int j = 1; j <= n; j++) {
            if (pivotBar - j < 0 || pivotBar + j > maxIdx) return false;
            if (ctx.getLow(pivotBar - j) <= pivotLow) return false;
            if (ctx.getLow(pivotBar + j) <= pivotLow) return false;
        }
        return true;
    }

    private boolean isLocalHigh(DetectorContext ctx, int pivotBar, int n) {
        double pivotHigh = ctx.getHigh(pivotBar);
        int maxIdx = ctx.getCurrentIndex();
        for (int j = 1; j <= n; j++) {
            if (pivotBar - j < 0 || pivotBar + j > maxIdx) return false;
            if (ctx.getHigh(pivotBar - j) >= pivotHigh) return false;
            if (ctx.getHigh(pivotBar + j) >= pivotHigh) return false;
        }
        return true;
    }

    /**
     * Estimates CVD at pivotBar by subtracting the deltas of bars
     * (pivotBar+1) through currentBar from the current CVD.
     */
    private double estimateCvdAtPivot(DetectorContext ctx, int pivotBar, int currentBar) {
        double adjust = 0.0;
        for (int k = pivotBar + 1; k <= currentBar; k++) {
            adjust += ctx.getDelta(k);
        }
        return cumulativeDelta - adjust;
    }
}
