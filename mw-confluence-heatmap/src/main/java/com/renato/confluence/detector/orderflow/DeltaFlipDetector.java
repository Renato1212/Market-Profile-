package com.renato.confluence.detector.orderflow;

import com.renato.confluence.detector.BaseDetector;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.util.RollingStats;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Detects sign flips in the CVD (Cumulative Volume Delta) slope.
 *
 * Algorithm:
 *  - Maintains a rolling array of CVD values.
 *  - Computes slope_i = (cvd_i - cvd_{i-SLOPE_PERIOD}) / SLOPE_PERIOD
 *  - Detects sign flip: slope changes from + to – or – to +.
 *  - Trigger: sign flip AND |slopeChange| > rollingMean(|slopeChange|, 50)
 *  - Strength: |slopeChange| / rollingMean(|slopeChange|, 50)
 */
public final class DeltaFlipDetector extends BaseDetector {

    private static final int    SLOPE_PERIOD   = 5;
    private static final int    MAX_HISTORY    = 4096;
    private static final LevelType[] TYPES     = { LevelType.DELTA_FLIP };

    private final List<Double> cvdHistory    = new ArrayList<>(MAX_HISTORY);
    private final RollingStats absSlopeStats = new RollingStats(50);

    private double cumulativeDelta  = 0.0;
    private double prevSlope        = Double.NaN;

    public DeltaFlipDetector() {
        super(true);
    }

    public DeltaFlipDetector(boolean enabled) {
        super(enabled);
    }

    @Override
    public LevelType[] producedTypes() {
        return TYPES;
    }

    @Override
    public void onBarClose(DetectorContext ctx) {
        int i = ctx.getCurrentIndex();

        // Accumulate CVD
        double delta = ctx.getDelta(i);
        cumulativeDelta += delta;
        cvdHistory.add(cumulativeDelta);

        int histSize = cvdHistory.size();
        if (histSize <= SLOPE_PERIOD) return;

        // Compute current slope
        double cvdNow  = cvdHistory.get(histSize - 1);
        double cvdPrev = cvdHistory.get(histSize - 1 - SLOPE_PERIOD);
        double slope   = (cvdNow - cvdPrev) / SLOPE_PERIOD;

        if (Double.isNaN(prevSlope)) {
            prevSlope = slope;
            absSlopeStats.push(0.0);
            return;
        }

        double slopeChange = slope - prevSlope;
        absSlopeStats.push(Math.abs(slopeChange));

        boolean signFlip = (prevSlope > 0 && slope < 0) || (prevSlope < 0 && slope > 0);
        prevSlope = slope;

        if (!signFlip) return;
        if (!absSlopeStats.isFull()) return;

        double meanAbsChange = absSlopeStats.getMean();
        if (meanAbsChange <= 0) return;

        double absChange = Math.abs(slopeChange);
        if (absChange <= meanAbsChange) return;

        // Trigger
        double rawStrength = absChange / meanAbsChange;
        double midPrice    = (ctx.getHigh(i) + ctx.getLow(i)) / 2.0;

        Map<String, Object> meta = new HashMap<>();
        meta.put("slopeChange", slopeChange);
        meta.put("slope", slope);
        meta.put("cvd", cumulativeDelta);

        emit(new Level(
                midPrice, midPrice, rawStrength,
                LevelType.DELTA_FLIP,
                ctx.getStartTime(i), i,
                meta));
    }

    @Override
    public void reset() {
        super.reset();
        cvdHistory.clear();
        absSlopeStats.reset();
        cumulativeDelta = 0.0;
        prevSlope = Double.NaN;
    }
}
