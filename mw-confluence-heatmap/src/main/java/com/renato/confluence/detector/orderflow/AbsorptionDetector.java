package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.util.RollingStats;

import java.util.HashMap;
import java.util.Map;

/**
 * Detects absorption bars: high-volume bars with narrow range and strong delta,
 * indicating that one side is absorbing aggressive order flow.
 *
 * Trigger conditions (all must be true):
 *  - volume > 2 × SMA(volume, 20)           [high effort]
 *  - (high - low) < 0.5 × ATR              [narrow range — limited result]
 *  - |z(delta, 50)| > 1.5                  [directional pressure present]
 *
 * Level: [bar.low, bar.high] (zone, not a point)
 *
 * Strength: z(vol, 20) × |z(delta, 50)| × (ATR / max(range, tickSize))
 */
public final class AbsorptionDetector extends BaseDetector {

    private static final double VOL_MULTIPLIER_THRESHOLD = 2.0;
    private static final double RANGE_ATR_FRACTION       = 0.5;
    private static final double DELTA_Z_THRESHOLD        = 1.5;
    private static final LevelType[] TYPES               = { LevelType.ABSORPTION };

    public AbsorptionDetector() {
        super(true);
    }

    public AbsorptionDetector(boolean enabled) {
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

        RollingStats volumeStats = ctx.getVolumeStats();
        RollingStats deltaStats  = ctx.getDeltaStats();
        if (!volumeStats.isFull() || !deltaStats.isFull()) return;

        double volume   = ctx.getVolume(i);
        double barHigh  = ctx.getHigh(i);
        double barLow   = ctx.getLow(i);
        double atr      = ctx.getAtr14();
        double tickSize = ctx.getTickSize();
        double delta    = ctx.getDelta(i);

        double volSma = volumeStats.getSMA();
        if (volSma <= 0 || volume < VOL_MULTIPLIER_THRESHOLD * volSma) return;

        double range = barHigh - barLow;
        if (range >= RANGE_ATR_FRACTION * atr) return;

        double zDelta  = Math.abs(deltaStats.getZScore(delta));
        if (zDelta < DELTA_Z_THRESHOLD) return;

        // All conditions met — compute strength
        double zVol       = volumeStats.getZScore(volume);
        double effectRange = Math.max(range, tickSize);
        double rawStrength = zVol * zDelta * (atr / effectRange);

        Map<String, Object> meta = new HashMap<>();
        meta.put("zDelta", zDelta);
        meta.put("zVol", zVol);
        meta.put("range", range);
        meta.put("volume", volume);

        emit(new Level(
                barLow, barHigh, rawStrength,
                LevelType.ABSORPTION,
                ctx.getStartTime(i), i,
                meta));
    }
}
