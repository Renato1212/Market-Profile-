package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.util.RollingStats;

import java.util.HashMap;
import java.util.Map;

/**
 * Detects stacked imbalances in the footprint chart.
 *
 * An imbalance occurs at a price tick when one side's volume is ≥ IMBALANCE_RATIO
 * times the other side.  A "stacked imbalance" is MIN_STACK_COUNT or more consecutive
 * imbalance ticks in the same direction within a single bar.
 *
 * Requires Order Flow Edition (footprint data).  If unavailable, silently skips
 * (logs one WARN per study session).
 *
 * Buy imbalance:  askVol ≥ IMBALANCE_RATIO × bidVol  AND  askVol > MIN_VOL_PER_TICK
 * Sell imbalance: bidVol ≥ IMBALANCE_RATIO × askVol  AND  bidVol > MIN_VOL_PER_TICK
 *
 * Strength: stackLength × maxRatio × log(1 + totalImbalanceVol / SMA(vol, 20))
 */
public final class StackedImbalanceDetector extends BaseDetector {

    private static final double IMBALANCE_RATIO    = 3.0;
    private static final double MIN_VOL_PER_TICK   = 5.0;
    private static final int    MIN_STACK_COUNT    = 3;
    private static final LevelType[] TYPES         = {
        LevelType.STACKED_IMBALANCE_BUY,
        LevelType.STACKED_IMBALANCE_SELL
    };

    private boolean footprintWarnLogged = false;

    public StackedImbalanceDetector() {
        super(true);
    }

    public StackedImbalanceDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();

        if (!ctx.isFootprintAvailable()) {
            if (!footprintWarnLogged) {
                ctx.log("WARN", "StackedImbalanceDetector: footprint data unavailable — "
                        + "Order Flow Edition required.  Detector will produce no signals.");
                footprintWarnLogged = true;
            }
            return;
        }

        RollingStats volumeStats = ctx.getVolumeStats();
        double volSma   = volumeStats.getSMA();
        double tickSize = ctx.getTickSize();
        double barLow   = ctx.getLow(i);
        double barHigh  = ctx.getHigh(i);

        if (tickSize <= 0) return;

        int steps = (int) Math.ceil((barHigh - barLow) / tickSize);

        // Walk price ticks bottom-up
        int    buyStreak   = 0;
        int    sellStreak  = 0;
        double buyStackLow    = Double.NaN;
        double sellStackLow   = Double.NaN;
        double buyMaxRatio    = 0;
        double sellMaxRatio   = 0;
        double buyTotalVol    = 0;
        double sellTotalVol   = 0;

        for (int s = 0; s <= steps; s++) {
            double price  = barLow + s * tickSize;
            double bidVol = ctx.getFootprintBidVolume(i, price);
            double askVol = ctx.getFootprintAskVolume(i, price);

            boolean isBuyImbalance  = askVol >= IMBALANCE_RATIO * Math.max(bidVol, 1e-9)
                                   && askVol >= MIN_VOL_PER_TICK;
            boolean isSellImbalance = bidVol >= IMBALANCE_RATIO * Math.max(askVol, 1e-9)
                                   && bidVol >= MIN_VOL_PER_TICK;

            // ---- Buy imbalance stack tracking --------------------------------
            if (isBuyImbalance) {
                if (buyStreak == 0) buyStackLow = price;
                buyStreak++;
                double ratio = askVol / Math.max(bidVol, 1e-9);
                if (ratio > buyMaxRatio) buyMaxRatio = ratio;
                buyTotalVol += askVol + bidVol;
            } else {
                if (buyStreak >= MIN_STACK_COUNT) {
                    emitBuyStack(ctx, i, buyStackLow,
                            barLow + (s - 1) * tickSize,
                            buyStreak, buyMaxRatio, buyTotalVol, volSma);
                }
                buyStreak  = 0;
                buyMaxRatio = 0;
                buyTotalVol = 0;
            }

            // ---- Sell imbalance stack tracking -------------------------------
            if (isSellImbalance) {
                if (sellStreak == 0) sellStackLow = price;
                sellStreak++;
                double ratio = bidVol / Math.max(askVol, 1e-9);
                if (ratio > sellMaxRatio) sellMaxRatio = ratio;
                sellTotalVol += askVol + bidVol;
            } else {
                if (sellStreak >= MIN_STACK_COUNT) {
                    emitSellStack(ctx, i, sellStackLow,
                            barLow + (s - 1) * tickSize,
                            sellStreak, sellMaxRatio, sellTotalVol, volSma);
                }
                sellStreak   = 0;
                sellMaxRatio = 0;
                sellTotalVol = 0;
            }
        }

        // Handle streaks that run to the top of the bar
        if (buyStreak >= MIN_STACK_COUNT) {
            emitBuyStack(ctx, i, buyStackLow, barHigh,
                    buyStreak, buyMaxRatio, buyTotalVol, volSma);
        }
        if (sellStreak >= MIN_STACK_COUNT) {
            emitSellStack(ctx, i, sellStackLow, barHigh,
                    sellStreak, sellMaxRatio, sellTotalVol, volSma);
        }
    }

    @Override
    public void reset() {
        super.reset();
        footprintWarnLogged = false;
    }

    // ------------------------------------------------------------------ helpers

    private void emitBuyStack(DetectorContext ctx, int barIndex,
                              double priceLow, double priceHigh,
                              int stackLen, double maxRatio,
                              double totalVol, double volSma) {
        double strength = stackLen * maxRatio
                * Math.log1p(volSma > 0 ? totalVol / volSma : totalVol);

        Map<String, Object> meta = new HashMap<>();
        meta.put("stackLen", stackLen);
        meta.put("maxRatio", maxRatio);
        meta.put("totalVol", totalVol);

        emit(new Level(
                priceLow, priceHigh, strength,
                LevelType.STACKED_IMBALANCE_BUY,
                ctx.getStartTime(barIndex), barIndex,
                meta));
    }

    private void emitSellStack(DetectorContext ctx, int barIndex,
                               double priceLow, double priceHigh,
                               int stackLen, double maxRatio,
                               double totalVol, double volSma) {
        double strength = stackLen * maxRatio
                * Math.log1p(volSma > 0 ? totalVol / volSma : totalVol);

        Map<String, Object> meta = new HashMap<>();
        meta.put("stackLen", stackLen);
        meta.put("maxRatio", maxRatio);
        meta.put("totalVol", totalVol);

        emit(new Level(
                priceLow, priceHigh, strength,
                LevelType.STACKED_IMBALANCE_SELL,
                ctx.getStartTime(barIndex), barIndex,
                meta));
    }
}
