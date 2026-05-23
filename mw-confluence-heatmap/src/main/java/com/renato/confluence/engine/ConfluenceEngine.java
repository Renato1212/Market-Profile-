package com.renato.confluence.engine;

import com.renato.confluence.domain.Cluster;
import com.renato.confluence.domain.DensityFunction;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;

import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Orchestrates the full confluence-computation pipeline:
 *
 *  1. Time decay + drop decayed levels
 *  2. Status update (touches / breaks)
 *  3. Per-detector (per-LevelType) max-scaling normalisation
 *  4. User-configurable weighting
 *  5. Greedy spatial clustering
 *  6. Kernel density estimation → DensityFunction
 *
 * Pure Java — no SDK imports.  Stateless: all state lives in the caller.
 */
public final class ConfluenceEngine {

    // ====================================================================== Settings

    public static final class Settings {

        /** Global half-life override in bars; 0 = use per-type defaults. */
        public final int halfLifeOverride;

        /** Drop levels whose decayed strength falls below this threshold. */
        public final double epsilonDecay;

        /**
         * Cluster epsilon expressed in ticks.
         * Final epsilon = max(clusterTicksEpsilon * tickSize, clusterAtrMultiplier * atr).
         */
        public final int clusterTicksEpsilon;

        /** Cluster epsilon as a fraction of ATR. */
        public final double clusterAtrMultiplier;

        /** Minimum KDE bandwidth = kdeHMinAtrMultiplier * atr. */
        public final double kdeHMinAtrMultiplier;

        /**
         * Maximum lookback bars.  Levels older than currentBar - maxLookbackBars
         * are silently dropped before time-decay runs (pre-filter for performance).
         */
        public final int maxLookbackBars;

        /** Per-LevelType weight overrides (percentage; 100 = default). */
        public final Map<LevelType, Integer> userWeights;

        public Settings(int halfLifeOverride,
                        double epsilonDecay,
                        int clusterTicksEpsilon,
                        double clusterAtrMultiplier,
                        double kdeHMinAtrMultiplier,
                        int maxLookbackBars,
                        Map<LevelType, Integer> userWeights) {
            this.halfLifeOverride     = halfLifeOverride;
            this.epsilonDecay         = epsilonDecay;
            this.clusterTicksEpsilon  = clusterTicksEpsilon;
            this.clusterAtrMultiplier = clusterAtrMultiplier;
            this.kdeHMinAtrMultiplier = kdeHMinAtrMultiplier;
            this.maxLookbackBars      = maxLookbackBars;

            EnumMap<LevelType, Integer> copy = new EnumMap<>(LevelType.class);
            copy.putAll(userWeights);
            this.userWeights = Collections.unmodifiableMap(copy);
        }

        public static Settings defaults() {
            return new Settings(
                    0,     // use per-type half-life defaults
                    0.01,  // epsilon decay
                    4,     // cluster ticks epsilon
                    0.15,  // cluster ATR multiplier
                    0.25,  // KDE h_min ATR multiplier
                    2000,  // max lookback bars
                    Collections.emptyMap());
        }
    }

    // ====================================================================== Main compute

    /**
     * Runs the full pipeline and returns the resulting {@link DensityFunction}.
     *
     * @param allLevels  all levels accumulated since study load
     * @param currentBar current bar index (levels older than maxLookback are dropped)
     * @param highs      bar high array (0 = oldest)
     * @param lows       bar low array
     * @param opens      bar open array
     * @param closes     bar close array
     * @param atr        current ATR14 (or equivalent)
     * @param tickSize   minimum price increment of the instrument
     * @param priceMin   lower bound of the density grid (e.g. currentClose - 5*ATR)
     * @param priceMax   upper bound of the density grid
     * @param settings   engine tuning parameters
     * @return normalised density function
     */
    public static DensityFunction compute(
            List<Level> allLevels,
            int currentBar,
            double[] highs, double[] lows, double[] opens, double[] closes,
            double atr, double tickSize,
            double priceMin, double priceMax,
            Settings settings) {

        if (allLevels.isEmpty()) {
            return new DensityFunction(Collections.emptyList());
        }

        // --- Pre-filter: drop levels beyond maxLookbackBars -------------------
        int lookbackCutoff = currentBar - settings.maxLookbackBars;
        List<Level> pooled = allLevels;
        if (lookbackCutoff > 0) {
            pooled = new java.util.ArrayList<>(allLevels.size());
            for (Level l : allLevels) {
                if (l.barIndex >= lookbackCutoff) pooled.add(l);
            }
        }

        // --- Step 1: Time decay -----------------------------------------------
        Map<String, Integer> halfLifeMap = new HashMap<>();
        if (settings.halfLifeOverride > 0) {
            for (LevelType t : LevelType.values()) {
                halfLifeMap.put(t.name(), settings.halfLifeOverride);
            }
        }
        List<Level> surviving = TimeDecay.apply(pooled, currentBar,
                halfLifeMap, settings.epsilonDecay);

        if (surviving.isEmpty()) {
            return new DensityFunction(Collections.emptyList());
        }

        // --- Step 2: Status update (touches / breaks) -------------------------
        surviving = StatusUpdater.markTouchesAndBreaks(
                surviving, highs, lows, opens, closes, currentBar, atr);

        if (surviving.isEmpty()) {
            return new DensityFunction(Collections.emptyList());
        }

        // --- Step 3: Per-detector normalisation --------------------------------
        surviving = Normalizer.maxScaleWithinDetector(surviving);

        // --- Step 4: User weighting -------------------------------------------
        surviving = Weighter.applyUserWeights(surviving, settings.userWeights);

        // --- Step 5: Clustering -----------------------------------------------
        double epsilon = Math.max(
                settings.clusterTicksEpsilon * tickSize,
                settings.clusterAtrMultiplier * atr);
        List<Cluster> clusters = Clusterer.greedyMerge(surviving, epsilon);

        // --- Step 6: KDE ------------------------------------------------------
        return KernelDensityEstimator.compute(
                clusters, priceMin, priceMax, tickSize, atr,
                settings.kdeHMinAtrMultiplier);
    }

    private ConfluenceEngine() {}
}
