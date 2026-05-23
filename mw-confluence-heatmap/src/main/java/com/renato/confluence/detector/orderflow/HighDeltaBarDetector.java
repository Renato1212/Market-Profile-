package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.util.RollingStats;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Detects bars with statistically extreme delta (order flow imbalance).
 *
 * Trigger: |z(delta, 50)| > 2.0 at bar close.
 *
 * Level price: bar's POC computed from footprint data if available,
 *              otherwise falls back to bar close.
 *
 * Raw strength: |z(delta, 50)| × log(1 + volume / SMA(volume, 20))
 */
public final class HighDeltaBarDetector extends BaseDetector {

    private static final double Z_THRESHOLD    = 2.0;
    private static final LevelType[] TYPES     = { LevelType.HIGH_DELTA_BAR };

    public HighDeltaBarDetector() {
        super(true);
    }

    public HighDeltaBarDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();
        if (i < 1) return;

        RollingStats deltaStats  = ctx.getDeltaStats();
        RollingStats volumeStats = ctx.getVolumeStats();
        if (!deltaStats.isFull()) return;   // wait for 50-bar warm-up

        double delta  = ctx.getDelta(i);
        double volume = ctx.getVolume(i);
        double zDelta = Math.abs(deltaStats.getZScore(delta));

        if (zDelta < Z_THRESHOLD) return;

        // Compute raw strength
        double volSma = volumeStats.getSMA();
        double strengthMult = (volSma > 0)
                ? Math.log1p(volume / volSma)
                : Math.log1p(1.0);
        double rawStrength = zDelta * strengthMult;

        // Determine level price
        double levelPrice = findBarPoc(ctx, i);

        Map<String, Object> meta = new HashMap<>();
        meta.put("zDelta", zDelta);
        meta.put("delta", delta);
        meta.put("volume", volume);

        emit(new Level(
                levelPrice, levelPrice, rawStrength,
                LevelType.HIGH_DELTA_BAR,
                ctx.getStartTime(i), i,
                meta));
    }

    // ------------------------------------------------------------------ helpers

    /**
     * Returns the price of maximum volume within the bar (POC).
     * Uses footprint data when available; otherwise falls back to bar close.
     */
    private double findBarPoc(DetectorContext ctx, int barIndex) {
        if (!ctx.isFootprintAvailable()) {
            return ctx.getClose(barIndex);
        }

        double tickSize = ctx.getTickSize();
        double barLow   = ctx.getLow(barIndex);
        double barHigh  = ctx.getHigh(barIndex);

        double maxVol      = -1;
        double pocPrice    = ctx.getClose(barIndex);
        int    steps       = (int) Math.ceil((barHigh - barLow) / tickSize);

        for (int s = 0; s <= steps; s++) {
            double price = barLow + s * tickSize;
            double vol   = ctx.getFootprintBidVolume(barIndex, price)
                         + ctx.getFootprintAskVolume(barIndex, price);
            if (vol > maxVol) {
                maxVol   = vol;
                pocPrice = price;
            }
        }
        return pocPrice;
    }
}
