package com.renato.confluence.util;

/**
 * Online incremental statistics over a fixed-size sliding window.
 * Uses Welford's algorithm for numerically stable variance computation.
 * Thread-unsafe — designed for single-threaded use inside MotiveWave calculate().
 */
public final class RollingStats {

    private final int    window;
    private final double[] buf;
    private int  head  = 0;     // next write index (circular)
    private int  count = 0;     // number of values pushed so far

    // Welford accumulators over the full window
    private double mean   = 0.0;
    private double m2     = 0.0;  // sum of squared deviations
    private double sum    = 0.0;  // simple sum for fast SMA

    public RollingStats(int window) {
        if (window < 1) throw new IllegalArgumentException("window must be >= 1");
        this.window = window;
        this.buf    = new double[window];
    }

    /**
     * Add a new data point.  When the window is full, the oldest value is evicted.
     */
    public void push(double value) {
        if (count < window) {
            // Window not yet full — simple online update
            buf[head] = value;
            head = (head + 1) % window;
            count++;

            // Welford online update (growing window)
            double delta  = value - mean;
            mean += delta / count;
            double delta2 = value - mean;
            m2   += delta * delta2;
            sum  += value;
        } else {
            // Evict oldest value and recompute accumulators from scratch to avoid
            // numerical drift over long series.  O(window) but window is bounded.
            double oldest = buf[head];
            buf[head] = value;
            head = (head + 1) % window;
            // count stays == window

            sum  = sum - oldest + value;
            mean = sum / window;

            // Recompute m2 for accuracy
            double newM2 = 0.0;
            for (double v : buf) {
                double d = v - mean;
                newM2 += d * d;
            }
            m2 = newM2;
        }
    }

    /** Current mean over the window (or all values pushed so far if fewer than window). */
    public double getMean() {
        return count == 0 ? 0.0 : mean;
    }

    /**
     * Population standard deviation over the current window contents.
     * Returns 0 if fewer than 2 values have been pushed.
     */
    public double getStd() {
        int n = Math.min(count, window);
        if (n < 2) return 0.0;
        return Math.sqrt(Math.max(m2 / n, 0.0));
    }

    /**
     * Sample variance (sum-of-sq-devs / (n-1)) over the current window.
     */
    public double getVariance() {
        int n = Math.min(count, window);
        if (n < 2) return 0.0;
        return Math.max(m2 / (n - 1), 0.0);
    }

    /**
     * Z-score of {@code value} relative to the current window statistics.
     * Uses population std dev; denominator is clamped to 1e-10 to avoid division by zero.
     */
    public double getZScore(double value) {
        double std = getStd();
        return (value - getMean()) / Math.max(std, 1e-10);
    }

    /**
     * Simple moving average (same as {@link #getMean()}).
     * Provided for clarity at call sites that only need the SMA.
     */
    public double getSMA() {
        return getMean();
    }

    /** Number of values pushed so far (saturates at window size after window fills). */
    public int getCount() {
        return count;
    }

    /** True once the window has been filled at least once. */
    public boolean isFull() {
        return count >= window;
    }

    /** Return the window size. */
    public int getWindow() {
        return window;
    }

    /** Reset all accumulators — useful when the study resets on chart reload. */
    public void reset() {
        head  = 0;
        count = 0;
        mean  = 0.0;
        m2    = 0.0;
        sum   = 0.0;
        java.util.Arrays.fill(buf, 0.0);
    }
}
