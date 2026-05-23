package com.renato.confluence.detector;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.List;

/**
 * Contract for all level detectors.
 *
 * The study calls {@link #onBarUpdate} on every tick/sub-bar update and
 * {@link #onBarClose} once per completed bar.  After calling all detectors
 * the study drains each detector's emitted levels via {@link #drainEmittedLevels}.
 *
 * Pure Java interface — no SDK imports.
 */
public interface LevelDetector {

    /** The LevelType(s) this detector can produce. */
    LevelType[] producedTypes();

    /**
     * Called on every bar update (tick or sub-bar).
     * Detectors that only need bar-close data should ignore this.
     */
    void onBarUpdate(DetectorContext ctx);

    /**
     * Called once when a bar has closed.
     * Primary calculation hook — most detectors do their work here.
     */
    void onBarClose(DetectorContext ctx);

    /**
     * Returns and clears all levels emitted since the last drain.
     * Must not return null; an empty list is acceptable.
     */
    List<Level> drainEmittedLevels();

    /**
     * Resets all internal state.  Called when the study reloads or the
     * user changes settings that require a full historical replay.
     */
    void reset();

    /** Returns false when the detector has been disabled via settings. */
    boolean isEnabled();
}
