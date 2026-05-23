package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Applies user-configurable per-LevelType weights to the normalised strengths.
 * Weights are expressed as percentages (0–200+), stored as integers.
 * A weight of 100 leaves strength unchanged; 200 doubles it; 0 zeroes it.
 *
 * Pure Java — no SDK imports.
 */
public final class Weighter {

    /**
     * Multiplies each level's {@code rawStrength} by {@code weight / 100.0}.
     * If no override exists for a type the per-type default weight is used.
     *
     * @param levels      normalised input levels
     * @param userWeights map of LevelType → weight% override (may be empty)
     * @return new list with weighted strengths
     */
    public static List<Level> applyUserWeights(List<Level> levels,
                                               Map<LevelType, Integer> userWeights) {
        if (levels.isEmpty()) return new ArrayList<>();

        List<Level> result = new ArrayList<>(levels.size());
        for (Level l : levels) {
            int weight = userWeights.getOrDefault(l.type, l.type.defaultWeight);
            double weighted = l.rawStrength * (weight / 100.0);
            result.add(TimeDecay.levelWithStrength(l, weighted));
        }
        return result;
    }

    private Weighter() {}
}
