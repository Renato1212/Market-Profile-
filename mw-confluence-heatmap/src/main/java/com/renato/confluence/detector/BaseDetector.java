package com.renato.confluence.detector;

import com.renato.confluence.domain.Level;

import java.util.ArrayList;
import java.util.List;

/**
 * Abstract base class implementing the boilerplate of {@link LevelDetector}.
 *
 * Subclasses call {@link #emit(Level)} to queue a detected level.
 * The study harvests levels via {@link #drainEmittedLevels()}.
 *
 * Pure Java — no SDK imports.
 */
public abstract class BaseDetector implements LevelDetector {

    private final List<Level> emitted = new ArrayList<>();
    private boolean enabled;

    protected BaseDetector(boolean enabledByDefault) {
        this.enabled = enabledByDefault;
    }

    // ------------------------------------------------------------------ emission

    /**
     * Queue a detected level.  Called by subclass implementations.
     * Silently ignored when the detector is disabled.
     */
    protected final void emit(Level level) {
        if (enabled) {
            emitted.add(level);
        }
    }

    @Override
    public final List<Level> drainEmittedLevels() {
        if (emitted.isEmpty()) return new ArrayList<>();
        List<Level> result = new ArrayList<>(emitted);
        emitted.clear();
        return result;
    }

    // ------------------------------------------------------------------ lifecycle defaults

    /**
     * Default no-op — subclasses override if they need tick-level updates.
     */
    @Override
    public void onBarUpdate(DetectorContext ctx) {
        // no-op by default
    }

    /**
     * Default no-op — subclasses override for bar-close logic.
     */
    @Override
    public void onBarClose(DetectorContext ctx) {
        // no-op by default
    }

    @Override
    public void reset() {
        emitted.clear();
    }

    // ------------------------------------------------------------------ enabled flag

    @Override
    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }
}
