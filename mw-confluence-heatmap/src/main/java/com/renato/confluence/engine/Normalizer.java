package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Per-detector (per-LevelType) max-scaling normalisation.
 * Each LevelType's maximum rawStrength is found and all levels of that type
 * are divided by it, mapping them into [0, 1].
 *
 * Pure Java — no SDK imports.
 */
public final class Normalizer {

    /**
     * Normalises {@code levels} per-type so the strongest level of each type
     * receives rawStrength = 1.0 and all others are scaled proportionally.
     *
     * @param levels input levels (not modified)
     * @return new list with normalised strengths
     */
    public static List<Level> maxScaleWithinDetector(List<Level> levels) {
        if (levels.isEmpty()) return new ArrayList<>();

        // Pass 1: find maximum strength per LevelType
        Map<LevelType, Double> maxByType = new EnumMap<>(LevelType.class);
        for (Level l : levels) {
            maxByType.merge(l.type, l.rawStrength, Math::max);
        }

        // Pass 2: scale each level
        List<Level> result = new ArrayList<>(levels.size());
        for (Level l : levels) {
            double max = maxByType.getOrDefault(l.type, 1.0);
            double normalised;
            if (max <= 0.0) {
                normalised = 0.0;
            } else {
                normalised = l.rawStrength / max;
            }
            result.add(TimeDecay.levelWithStrength(l, normalised));
        }
        return result;
    }

    private Normalizer() {}
}
