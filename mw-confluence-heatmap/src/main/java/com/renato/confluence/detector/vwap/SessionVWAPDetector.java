package com.renato.confluence.detector.vwap;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Computes session VWAP and its first two standard deviation bands using an
 * online (Knuth-Welford) algorithm.  Emits five levels on every bar update:
 *
 *   SESSION_VWAP          — session volume-weighted average price
 *   VWAP_SIGMA_POS_1 / _NEG_1  — VWAP ± 1 σ
 *   VWAP_SIGMA_POS_2 / _NEG_2  — VWAP ± 2 σ
 *
 * Accumulators reset at session boundaries ({@link DetectorContext#isSessionStart}).
 *
 * Typical price used: (high + low + close) / 3.
 */
public final class SessionVWAPDetector extends BaseDetector {

    private static final LevelType[] TYPES = {
        LevelType.SESSION_VWAP,
        LevelType.VWAP_SIGMA_POS_1,
        LevelType.VWAP_SIGMA_NEG_1,
        LevelType.VWAP_SIGMA_POS_2,
        LevelType.VWAP_SIGMA_NEG_2
    };

    // Running VWAP accumulators
    private double cumulativePV  = 0.0;   // Σ(typicalPrice * volume)
    private double cumulativeVol = 0.0;   // Σ(volume)
    private double cumulativePVV = 0.0;   // Σ(typicalPrice² * volume)

    public SessionVWAPDetector() {
        super(true);
    }

    public SessionVWAPDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarUpdate(DetectorContext ctx) {
        // VWAP is updated on bar close only — no intra-bar update needed
        // (overriding here for clarity; delegates to onBarClose logic)
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();

        // Reset at session start
        if (ctx.isSessionStart(i)) {
            resetAccumulators();
        }

        double high   = ctx.getHigh(i);
        double low    = ctx.getLow(i);
        double close  = ctx.getClose(i);
        double volume = ctx.getVolume(i);
        long   ts     = ctx.getStartTime(i);

        if (volume <= 0) return;

        double typicalPrice = (high + low + close) / 3.0;

        // Update accumulators
        cumulativePV  += typicalPrice * volume;
        cumulativeVol += volume;
        cumulativePVV += typicalPrice * typicalPrice * volume;

        if (cumulativeVol <= 0) return;

        double vwap     = cumulativePV / cumulativeVol;
        double variance = Math.max(0.0, (cumulativePVV / cumulativeVol) - (vwap * vwap));
        double stdDev   = Math.sqrt(variance);

        Map<String, Object> metaVwap = new HashMap<>();
        metaVwap.put("stdDev", stdDev);
        metaVwap.put("cumVol", cumulativeVol);

        emit(new Level(vwap, vwap, 1.0,
                LevelType.SESSION_VWAP, ts, i, metaVwap));

        emit(new Level(vwap + stdDev, vwap + stdDev, 0.8,
                LevelType.VWAP_SIGMA_POS_1, ts, i, Collections.emptyMap()));

        emit(new Level(vwap - stdDev, vwap - stdDev, 0.8,
                LevelType.VWAP_SIGMA_NEG_1, ts, i, Collections.emptyMap()));

        emit(new Level(vwap + 2 * stdDev, vwap + 2 * stdDev, 0.6,
                LevelType.VWAP_SIGMA_POS_2, ts, i, Collections.emptyMap()));

        emit(new Level(vwap - 2 * stdDev, vwap - 2 * stdDev, 0.6,
                LevelType.VWAP_SIGMA_NEG_2, ts, i, Collections.emptyMap()));
    }

    @Override
    public void reset() {
        super.reset();
        resetAccumulators();
    }

    private void resetAccumulators() {
        cumulativePV  = 0.0;
        cumulativeVol = 0.0;
        cumulativePVV = 0.0;
    }
}
