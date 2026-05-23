package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.util.RollingStats;

import java.util.HashMap;
import java.util.Map;

/**
 * Emits a level at the bar's Point of Control (price with maximum volume)
 * for high-volume bars.
 *
 * Trigger: volume > 2.0 × SMA(volume, 20)
 * Level:   POC of bar (footprint) or close (fallback)
 * Strength: log(1 + volume / SMA(volume, 20)) × 2
 */
public final class BarPOCDetector extends BaseDetector {

    private static final double VOLUME_MULTIPLIER_THRESHOLD = 2.0;
    private static final LevelType[] TYPES = { LevelType.BAR_POC };

    public BarPOCDetector() {
        super(true);
    }

    public BarPOCDetector(boolean enabled) {
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
        if (!volumeStats.isFull()) return;  // wait for 20-bar warm-up

        double volume = ctx.getVolume(i);
        double volSma = volumeStats.getSMA();

        if (volSma <= 0 || volume < VOLUME_MULTIPLIER_THRESHOLD * volSma) return;

        double pocPrice   = findBarPoc(ctx, i);
        double rawStrength = Math.log1p(volume / volSma) * 2.0;

        Map<String, Object> meta = new HashMap<>();
        meta.put("volume", volume);
        meta.put("volSma", volSma);
        meta.put("volumeRatio", volume / volSma);

        emit(new Level(
                pocPrice, pocPrice, rawStrength,
                LevelType.BAR_POC,
                ctx.getStartTime(i), i,
                meta));
    }

    // ------------------------------------------------------------------ helpers

    private double findBarPoc(DetectorContext ctx, int barIndex) {
        if (!ctx.isFootprintAvailable()) {
            return ctx.getClose(barIndex);
        }

        double tickSize = ctx.getTickSize();
        double barLow   = ctx.getLow(barIndex);
        double barHigh  = ctx.getHigh(barIndex);

        double maxVol   = -1;
        double pocPrice = ctx.getClose(barIndex);
        int    steps    = (int) Math.ceil((barHigh - barLow) / tickSize);

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
