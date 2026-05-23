package com.renato.confluence.util;

/**
 * Pure-Java static utilities for bar-level mathematics.
 * No SDK imports — fully unit-testable.
 */
public final class BarMath {

    private BarMath() {}

    /**
     * Wilder's ATR(period) ending at {@code index}.
     * Requires {@code closes[index - period .. index]} to be valid.
     * Returns {@code 0} if there are not enough bars.
     *
     * @param highs   bar high array (index 0 = oldest)
     * @param lows    bar low array
     * @param closes  bar close array (closes[i-1] = prior close for TR of bar i)
     * @param index   the bar to compute ATR up to (inclusive)
     * @param period  ATR period (>= 1)
     * @return Wilder ATR, or 0 if insufficient data
     */
    public static double atr(double[] highs, double[] lows, double[] closes,
                             int index, int period) {
        if (index < period || period < 1) return 0.0;
        if (highs.length != lows.length || lows.length != closes.length) {
            throw new IllegalArgumentException("Arrays must be the same length");
        }
        if (index >= closes.length) return 0.0;

        // Seed: simple average of first `period` true ranges
        int seedStart = index - period + 1;
        double atrVal = 0.0;
        for (int i = seedStart; i <= index; i++) {
            atrVal += trueRange(highs, lows, closes, i);
        }
        atrVal /= period;

        return atrVal;
    }

    /**
     * Wilder's smoothed ATR (RMA) computed from the beginning up to {@code index}.
     * More accurate than the simple-average seed above for long lookback.
     *
     * @param highs  bar high array
     * @param lows   bar low array
     * @param closes bar close array
     * @param index  compute up to this bar (inclusive)
     * @param period smoothing period
     * @return smoothed ATR, or 0 if insufficient data
     */
    public static double atrSmoothed(double[] highs, double[] lows, double[] closes,
                                     int index, int period) {
        if (index < period || period < 1) return 0.0;
        if (index >= closes.length) return 0.0;

        // Seed with first `period` bars
        double atrVal = 0.0;
        for (int i = 1; i <= period; i++) {
            atrVal += trueRange(highs, lows, closes, i);
        }
        atrVal /= period;

        // Wilder smoothing: ATR_n = (ATR_{n-1} * (period-1) + TR_n) / period
        for (int i = period + 1; i <= index; i++) {
            double tr = trueRange(highs, lows, closes, i);
            atrVal = (atrVal * (period - 1) + tr) / period;
        }
        return atrVal;
    }

    /**
     * True range of bar at {@code index}.
     * TR = max(high - low, |high - prevClose|, |low - prevClose|).
     * Falls back to (high - low) for the very first bar.
     */
    public static double trueRange(double[] highs, double[] lows, double[] closes, int index) {
        if (index <= 0 || index >= highs.length) {
            return highs[Math.max(index, 0)] - lows[Math.max(index, 0)];
        }
        double hl   = highs[index] - lows[index];
        double hpc  = Math.abs(highs[index] - closes[index - 1]);
        double lpc  = Math.abs(lows[index]  - closes[index - 1]);
        return Math.max(hl, Math.max(hpc, lpc));
    }

    /**
     * Simple Moving Average of {@code values[index - period + 1 .. index]}.
     *
     * @param values  source array
     * @param index   end index (inclusive)
     * @param period  number of bars to average
     * @return SMA, or the close itself if insufficient data
     */
    public static double sma(double[] values, int index, int period) {
        if (index < 0 || index >= values.length || period < 1) return 0.0;
        int start = Math.max(0, index - period + 1);
        double sum = 0.0;
        for (int i = start; i <= index; i++) {
            sum += values[i];
        }
        return sum / (index - start + 1);
    }

    /**
     * Returns the bar index within the current session (0-based).
     * Scans backward from {@code index} until a session-start bar or the array start.
     *
     * @param sessionStarts boolean array where true = first bar of a new session
     * @param index         current bar index
     * @return 0-based position within the session
     */
    public static int barInSession(boolean[] sessionStarts, int index) {
        if (index < 0) return 0;
        int n = 0;
        for (int i = index; i > 0; i--) {
            if (sessionStarts[i]) return n;
            n++;
        }
        return n;
    }

    /**
     * Rounds {@code price} to the nearest multiple of {@code tickSize}.
     */
    public static double roundToTick(double price, double tickSize) {
        if (tickSize <= 0) return price;
        return Math.round(price / tickSize) * tickSize;
    }

    /**
     * Returns the fractal swing-high index in the window [{@code from}, {@code to}]
     * using a symmetrical N-bar confirmation window.
     * Returns -1 if no swing high is found.
     */
    public static int swingHighIndex(double[] highs, int from, int to, int n) {
        if (from < 0 || to >= highs.length || from > to) return -1;
        for (int i = from + n; i <= to - n; i++) {
            boolean isHigh = true;
            for (int j = 1; j <= n; j++) {
                if (highs[i - j] >= highs[i] || highs[i + j] >= highs[i]) {
                    isHigh = false;
                    break;
                }
            }
            if (isHigh) return i;
        }
        return -1;
    }

    /**
     * Returns the fractal swing-low index in the window [{@code from}, {@code to}].
     * Returns -1 if none found.
     */
    public static int swingLowIndex(double[] lows, int from, int to, int n) {
        if (from < 0 || to >= lows.length || from > to) return -1;
        for (int i = from + n; i <= to - n; i++) {
            boolean isLow = true;
            for (int j = 1; j <= n; j++) {
                if (lows[i - j] <= lows[i] || lows[i + j] <= lows[i]) {
                    isLow = false;
                    break;
                }
            }
            if (isLow) return i;
        }
        return -1;
    }

    /**
     * Linear interpolation between two values.
     */
    public static double lerp(double a, double b, double t) {
        return a + t * (b - a);
    }
}
