package com.renato.confluence.detector.profile;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Emits prior RTH session high, low, and close as key reference levels.
 *
 * At each session boundary:
 *  1. Snapshots the completed session's high, low, and close.
 *  2. Emits PRIOR_DAY_HIGH, PRIOR_DAY_LOW, PRIOR_DAY_CLOSE on every subsequent bar.
 *
 * Strength: 1.0 baseline.  Levels that remain untested receive a 1.5× multiplier
 * (applied in meta; the engine may optionally honour it).
 *
 * Once a level is tested (price trades through it), the multiplier drops to 1.0.
 */
public final class PriorSessionLevelsDetector extends BaseDetector {

    private static final double UNTESTED_MULTIPLIER = 1.5;
    private static final LevelType[] TYPES = {
        LevelType.PRIOR_DAY_HIGH,
        LevelType.PRIOR_DAY_LOW,
        LevelType.PRIOR_DAY_CLOSE
    };

    // Prior session snapshot
    private double priorHigh  = Double.NaN;
    private double priorLow   = Double.NaN;
    private double priorClose = Double.NaN;
    private int    priorEmittedBar = -1;

    // Tested flags
    private boolean highTested  = false;
    private boolean lowTested   = false;
    private boolean closeTested = false;

    // Current session trackers
    private double sessionHigh  = Double.NEGATIVE_INFINITY;
    private double sessionLow   = Double.POSITIVE_INFINITY;
    private double sessionClose = Double.NaN;

    public PriorSessionLevelsDetector() {
        super(true);
    }

    public PriorSessionLevelsDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int    i    = ctx.getCurrentIndex();
        double hi   = ctx.getHigh(i);
        double lo   = ctx.getLow(i);
        double close = ctx.getClose(i);
        long   ts   = ctx.getStartTime(i);

        // Detect session boundary
        if (ctx.isSessionStart(i) && i > 0) {
            // Snapshot completed session as "prior"
            priorHigh      = sessionHigh;
            priorLow       = sessionLow;
            priorClose     = sessionClose;
            priorEmittedBar = i;
            highTested     = false;
            lowTested      = false;
            closeTested    = false;

            // Reset current session trackers
            sessionHigh  = Double.NEGATIVE_INFINITY;
            sessionLow   = Double.POSITIVE_INFINITY;
            sessionClose = Double.NaN;
        }

        // Update current session
        if (hi > sessionHigh) sessionHigh = hi;
        if (lo < sessionLow)  sessionLow  = lo;
        sessionClose = close;

        // Emit prior session levels if we have them
        if (Double.isNaN(priorHigh)) return;

        // Check tests
        if (!highTested  && hi >= priorHigh  && lo <= priorHigh)  highTested  = true;
        if (!lowTested   && hi >= priorLow   && lo <= priorLow)   lowTested   = true;
        if (!closeTested && hi >= priorClose && lo <= priorClose)  closeTested = true;

        double highStrength  = highTested  ? 1.0 : UNTESTED_MULTIPLIER;
        double lowStrength   = lowTested   ? 1.0 : UNTESTED_MULTIPLIER;
        double closeStrength = closeTested ? 1.0 : UNTESTED_MULTIPLIER;

        Map<String, Object> highMeta = new HashMap<>();
        highMeta.put("tested", highTested);
        emit(new Level(priorHigh, priorHigh, highStrength,
                LevelType.PRIOR_DAY_HIGH, ts, i, highMeta));

        Map<String, Object> lowMeta = new HashMap<>();
        lowMeta.put("tested", lowTested);
        emit(new Level(priorLow, priorLow, lowStrength,
                LevelType.PRIOR_DAY_LOW, ts, i, lowMeta));

        Map<String, Object> closeMeta = new HashMap<>();
        closeMeta.put("tested", closeTested);
        emit(new Level(priorClose, priorClose, closeStrength,
                LevelType.PRIOR_DAY_CLOSE, ts, i, closeMeta));
    }

    @Override
    public void reset() {
        super.reset();
        priorHigh    = Double.NaN;
        priorLow     = Double.NaN;
        priorClose   = Double.NaN;
        priorEmittedBar = -1;
        highTested   = false;
        lowTested    = false;
        closeTested  = false;
        sessionHigh  = Double.NEGATIVE_INFINITY;
        sessionLow   = Double.POSITIVE_INFINITY;
        sessionClose = Double.NaN;
    }
}
