package com.renato.confluence.detector;

import com.renato.confluence.util.RollingStats;

/**
 * Abstraction layer between detectors and the MotiveWave SDK.
 *
 * Detectors only depend on this interface, which means:
 *  (a) They can be unit-tested without any SDK on the classpath.
 *  (b) The SDK-side implementation can be swapped without touching detector logic.
 *
 * Pure Java interface — no SDK imports.
 */
public interface DetectorContext {

    // ------------------------------------------------------------------ Bar position

    /** Index of the bar currently being processed. */
    int getCurrentIndex();

    /** Total number of bars available in the data series. */
    int size();

    // ------------------------------------------------------------------ OHLCV

    double getClose(int index);
    double getHigh(int index);
    double getLow(int index);
    double getOpen(int index);
    double getVolume(int index);

    /** Start-of-bar timestamp in milliseconds since epoch. */
    long getStartTime(int index);

    // ------------------------------------------------------------------ Order flow (bar level)

    /**
     * Total bid volume for the bar.
     * Returns 0 if order-flow data is unavailable (non-OFE data feed).
     */
    double getBidVolume(int index);

    /**
     * Total ask volume for the bar.
     * Returns 0 if order-flow data is unavailable.
     */
    double getAskVolume(int index);

    /**
     * Bar delta = askVolume - bidVolume.
     * Returns 0 if order-flow data is unavailable.
     */
    double getDelta(int index);

    // ------------------------------------------------------------------ Footprint (OFE only)

    /**
     * Bid volume at a specific price tick within a bar.
     * Returns 0 if footprint data is unavailable for that bar/price.
     *
     * @param barIndex 0-based bar index
     * @param price    exact price tick (should be a valid tick boundary)
     */
    double getFootprintBidVolume(int barIndex, double price);

    /**
     * Ask volume at a specific price tick within a bar.
     * Returns 0 if footprint data is unavailable.
     */
    double getFootprintAskVolume(int barIndex, double price);

    /**
     * Returns true if per-price footprint (bid/ask by tick) data is available.
     * Detectors that require this must check and skip or warn when false.
     */
    boolean isFootprintAvailable();

    // ------------------------------------------------------------------ Instrument

    double getAtr14();
    double getTickSize();
    String getSymbol();

    // ------------------------------------------------------------------ Shared stats

    /**
     * Shared rolling 50-bar delta statistics (z-score, mean, std).
     * Pre-computed by the study before detectors run — O(1) per detector.
     */
    RollingStats getDeltaStats();

    /**
     * Shared rolling 20-bar volume statistics.
     * Pre-computed by the study before detectors run — O(1) per detector.
     */
    RollingStats getVolumeStats();

    // ------------------------------------------------------------------ Session

    /** Returns true if bar {@code index} is the first bar of a new RTH session. */
    boolean isSessionStart(int index);

    /** Returns true if bar {@code index} falls within the RTH session window. */
    boolean isRthSession(int index);

    // ------------------------------------------------------------------ Diagnostics

    /**
     * Log a message from within a detector.
     *
     * @param level   "DEBUG", "INFO", "WARN", "ERROR"
     * @param message log message
     */
    void log(String level, String message);
}
