package com.renato.confluence.detector.profile;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Builds a rolling session volume profile and emits:
 *  - DEVELOPING_POC  — live POC of the current session (updated every bar)
 *  - HVN             — High-Volume Nodes (local maxima in the volume profile)
 *  - LVN             — Low-Volume Nodes (local minima in the volume profile)
 *  - NAKED_POC       — prior session's POC that has not been retested
 *
 * Volume profile is built by distributing each bar's total volume at its
 * close price (tick-accurate if footprint is unavailable; POC-accurate otherwise).
 *
 * On session boundary:
 *  1. The current session profile is snapshotted.
 *  2. Its POC is checked for "naked" status (has price traded through it since?).
 *  3. HVN/LVN levels are emitted from the completed session.
 *  4. Profile resets for the new session.
 */
public final class SessionVolumeProfileDetector extends BaseDetector {

    private static final double HVN_MIN_PROMINENCE = 0.5;  // HVN bin must be >= 50% of max
    private static final double LVN_MAX_RATIO      = 0.25; // LVN bin must be < 25% of max
    private static final LevelType[] TYPES         = {
        LevelType.DEVELOPING_POC,
        LevelType.HVN,
        LevelType.LVN,
        LevelType.NAKED_POC
    };

    // Current session
    private final TreeMap<Double, Double> volumeByPrice = new TreeMap<>();
    private double sessionHigh = Double.NEGATIVE_INFINITY;
    private double sessionLow  = Double.POSITIVE_INFINITY;
    private int    sessionStartBar = 0;
    private double tickSize   = 0.0;

    // Prior session naked POC tracking
    private final List<NakedPocEntry> nakedPocs = new ArrayList<>();

    private static final class NakedPocEntry {
        final double price;
        final int emittedBar;
        boolean tested;

        NakedPocEntry(double price, int emittedBar) {
            this.price       = price;
            this.emittedBar  = emittedBar;
            this.tested      = false;
        }
    }

    public SessionVolumeProfileDetector() {
        super(true);
    }

    public SessionVolumeProfileDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();

        // Initialise tick size once
        if (tickSize <= 0) {
            tickSize = ctx.getTickSize();
            if (tickSize <= 0) tickSize = 0.01;
        }

        // Detect session boundary
        if (ctx.isSessionStart(i) && i > 0) {
            onSessionEnd(ctx, i - 1);
            onSessionStart(i);
        }

        // Update session extremes
        double hi = ctx.getHigh(i);
        double lo = ctx.getLow(i);
        if (hi > sessionHigh) sessionHigh = hi;
        if (lo < sessionLow)  sessionLow  = lo;

        // Add volume to profile
        double vol       = ctx.getVolume(i);
        double priceKey  = roundToTick(ctx.getClose(i), tickSize);
        volumeByPrice.merge(priceKey, vol, Double::sum);

        // Check naked POC tests
        for (NakedPocEntry entry : nakedPocs) {
            if (!entry.tested && hi >= entry.price && lo <= entry.price) {
                entry.tested = true;
            }
        }

        // Emit DEVELOPING_POC (live, every bar)
        double poc = findPoc();
        if (!Double.isNaN(poc)) {
            emit(new Level(
                    poc, poc, 1.0,
                    LevelType.DEVELOPING_POC,
                    ctx.getStartTime(i), i,
                    Collections.emptyMap()));
        }

        // Emit surviving naked POCs
        for (NakedPocEntry entry : nakedPocs) {
            if (!entry.tested) {
                emit(new Level(
                        entry.price, entry.price, 1.0,
                        LevelType.NAKED_POC,
                        ctx.getStartTime(i), i,
                        Collections.emptyMap()));
            }
        }
    }

    @Override
    public void reset() {
        super.reset();
        volumeByPrice.clear();
        nakedPocs.clear();
        sessionHigh = Double.NEGATIVE_INFINITY;
        sessionLow  = Double.POSITIVE_INFINITY;
        sessionStartBar = 0;
        tickSize = 0.0;
    }

    // ------------------------------------------------------------------ session transitions

    private void onSessionEnd(DetectorContext ctx, int lastBar) {
        if (volumeByPrice.isEmpty()) return;

        double poc = findPoc();
        long   ts  = ctx.getStartTime(lastBar);
        int    idx = lastBar;

        // Snapshot HVN / LVN from completed session
        emitProfileLevels(ctx, poc, ts, idx);

        // Register naked POC
        if (!Double.isNaN(poc)) {
            nakedPocs.add(new NakedPocEntry(poc, idx));
            // Keep list bounded
            if (nakedPocs.size() > 30) nakedPocs.remove(0);
        }
    }

    private void onSessionStart(int newBar) {
        volumeByPrice.clear();
        sessionHigh = Double.NEGATIVE_INFINITY;
        sessionLow  = Double.POSITIVE_INFINITY;
        sessionStartBar = newBar;
    }

    // ------------------------------------------------------------------ profile analysis

    private double findPoc() {
        double maxVol  = -1;
        double pocPrice = Double.NaN;
        for (Map.Entry<Double, Double> entry : volumeByPrice.entrySet()) {
            if (entry.getValue() > maxVol) {
                maxVol   = entry.getValue();
                pocPrice = entry.getKey();
            }
        }
        return pocPrice;
    }

    private void emitProfileLevels(DetectorContext ctx, double poc, long ts, int barIdx) {
        if (volumeByPrice.size() < 3) return;

        double maxVol = volumeByPrice.values().stream().mapToDouble(d -> d).max().orElse(0);
        if (maxVol <= 0) return;

        List<Double> prices = new ArrayList<>(volumeByPrice.keySet());
        Collections.sort(prices);

        for (int j = 1; j < prices.size() - 1; j++) {
            double p    = prices.get(j);
            double vol  = volumeByPrice.getOrDefault(p, 0.0);
            double volNorm = vol / maxVol;

            double prevVol = volumeByPrice.getOrDefault(prices.get(j - 1), 0.0);
            double nextVol = volumeByPrice.getOrDefault(prices.get(j + 1), 0.0);

            boolean isLocalMax = vol > prevVol && vol > nextVol;
            boolean isLocalMin = vol < prevVol && vol < nextVol;

            if (isLocalMax && volNorm >= HVN_MIN_PROMINENCE) {
                Map<String, Object> meta = new HashMap<>();
                meta.put("volNorm", volNorm);
                emit(new Level(p, p, volNorm, LevelType.HVN, ts, barIdx, meta));
            }

            if (isLocalMin && volNorm < LVN_MAX_RATIO) {
                Map<String, Object> meta = new HashMap<>();
                meta.put("volNorm", volNorm);
                emit(new Level(p, p, 1.0 - volNorm, LevelType.LVN, ts, barIdx, meta));
            }
        }
    }

    private static double roundToTick(double price, double tickSize) {
        if (tickSize <= 0) return price;
        return Math.round(price / tickSize) * tickSize;
    }
}
