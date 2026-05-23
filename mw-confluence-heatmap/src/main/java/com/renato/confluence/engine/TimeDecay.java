package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelStatus;
import com.renato.confluence.domain.LevelType;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Applies exponential time-decay to raw level strengths.
 * Pure Java — no SDK imports.
 */
public final class TimeDecay {

    private static final double DEFAULT_EPSILON_DECAY = 0.01;

    /**
     * Applies time-decay to each level and drops those whose decayed strength
     * falls below {@code epsilonDecay}.
     *
     * @param levels            input levels (immutable)
     * @param currentBar        the current bar index
     * @param halfLifeOverrides map of LevelType.name() → half-life override in bars;
     *                          if a type is absent, the per-type default is used
     * @param epsilonDecay      minimum survival threshold after decay
     * @return surviving levels with updated rawStrength
     */
    public static List<Level> apply(List<Level> levels, int currentBar,
                                    Map<String, Integer> halfLifeOverrides,
                                    double epsilonDecay) {
        if (levels.isEmpty()) return Collections.emptyList();

        List<Level> surviving = new ArrayList<>(levels.size());
        for (Level level : levels) {
            int halfLife = halfLifeOverrides.getOrDefault(level.type.name(),
                    level.type.defaultHalfLifeBars);

            int age = Math.max(0, currentBar - level.barIndex);

            double decayed;
            if (halfLife == Integer.MAX_VALUE) {
                // VWAP, round numbers, etc. — never decay
                decayed = level.rawStrength;
            } else if (halfLife <= 0) {
                // Treat 0 or negative as "instant decay" — drop immediately
                decayed = 0.0;
            } else {
                decayed = level.rawStrength * Math.exp(-(double) age / halfLife);
            }

            if (decayed >= epsilonDecay) {
                surviving.add(levelWithStrength(level, decayed));
            }
        }
        return surviving;
    }

    /**
     * Convenience overload using per-type defaults and the default epsilon.
     */
    public static List<Level> apply(List<Level> levels, int currentBar) {
        return apply(levels, currentBar, Collections.emptyMap(), DEFAULT_EPSILON_DECAY);
    }

    /**
     * Creates a new {@link Level} identical to {@code original} but with
     * {@code newStrength} substituted for {@code rawStrength}.
     * Used by the pipeline to propagate transformed strengths without breaking
     * Level's immutability contract.
     */
    static Level levelWithStrength(Level original, double newStrength) {
        return new Level(
                original.priceLow,
                original.priceHigh,
                newStrength,
                original.type,
                original.timestampMillis,
                original.barIndex,
                original.meta,
                original.status,
                original.touchCount);
    }

    private TimeDecay() {}
}
