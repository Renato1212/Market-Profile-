package com.renato.confluence.domain;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Immutable value object representing a single detected price level.
 * All mutation returns new instances (copy-on-write semantics).
 */
public final class Level {

    public final double              priceLow;
    public final double              priceHigh;
    public final double              rawStrength;   // current (possibly decayed) strength [0, ∞)
    public final LevelType           type;
    public final long                timestampMillis;
    public final int                 barIndex;      // bar index at emission
    public final Map<String, Object> meta;          // detector-specific extra data
    public final LevelStatus         status;
    public final int                 touchCount;

    /** Public constructor — meta values must be mutable at call site, will be copied. */
    public Level(double priceLow, double priceHigh, double rawStrength,
                 LevelType type, long timestampMillis, int barIndex,
                 Map<String, Object> meta) {
        this(priceLow, priceHigh, rawStrength, type, timestampMillis, barIndex,
             meta, LevelStatus.NEW, 0);
    }

    /** Full constructor — public so the engine layer can create modified copies. */
    public Level(double priceLow, double priceHigh, double rawStrength,
                 LevelType type, long timestampMillis, int barIndex,
                 Map<String, Object> meta, LevelStatus status, int touchCount) {
        this.priceLow       = priceLow;
        this.priceHigh      = priceHigh;
        this.rawStrength    = rawStrength;
        this.type           = type;
        this.timestampMillis = timestampMillis;
        this.barIndex       = barIndex;
        this.meta           = Collections.unmodifiableMap(new HashMap<>(meta));
        this.status         = status;
        this.touchCount     = touchCount;
    }

    // ------------------------------------------------------------------ derived

    public double midPrice() { return (priceLow + priceHigh) / 2.0; }
    public double width()    { return priceHigh - priceLow; }
    public boolean isPoint() { return Double.compare(priceLow, priceHigh) == 0; }

    // ------------------------------------------------------------------ copy-on-write

    public Level withStatus(LevelStatus newStatus) {
        return new Level(priceLow, priceHigh, rawStrength, type, timestampMillis,
                         barIndex, meta, newStatus, touchCount);
    }

    public Level withTouchCount(int newTouchCount) {
        return new Level(priceLow, priceHigh, rawStrength, type, timestampMillis,
                         barIndex, meta, status, newTouchCount);
    }

    // ------------------------------------------------------------------ Object

    @Override
    public String toString() {
        return String.format("Level{type=%s, mid=%.4f, raw=%.4f, status=%s, touches=%d}",
                type, midPrice(), rawStrength, status, touchCount);
    }
}
