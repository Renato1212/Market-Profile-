package com.renato.confluence.domain;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Immutable snapshot of the Kernel Density Estimate output.
 * All density values are normalised to [0, 1] relative to the maximum bin.
 */
public final class DensityFunction {

    // ------------------------------------------------------------------ Bin

    public static final class Bin {
        public final double price;
        public final double densityNorm;   // [0, 1] where 1 = maximum density

        public Bin(double price, double densityNorm) {
            this.price       = price;
            this.densityNorm = densityNorm;
        }

        @Override
        public String toString() {
            return String.format("Bin{price=%.4f, density=%.4f}", price, densityNorm);
        }
    }

    // ------------------------------------------------------------------ Fields

    private final List<Bin> bins;
    private final double    pocPrice;
    private final double    maxDensity;

    // ------------------------------------------------------------------ Constructor

    public DensityFunction(List<Bin> bins) {
        this.bins = List.copyOf(bins);
        if (bins.isEmpty()) {
            this.pocPrice   = Double.NaN;
            this.maxDensity = 0.0;
        } else {
            Bin poc = bins.stream()
                    .max((a, b) -> Double.compare(a.densityNorm, b.densityNorm))
                    .orElse(new Bin(0, 0));
            this.pocPrice   = poc.price;
            this.maxDensity = poc.densityNorm;
        }
    }

    // ------------------------------------------------------------------ Accessors

    public List<Bin> getBins()      { return bins; }
    public double    getPocPrice()  { return pocPrice; }
    public double    getMaxDensity(){ return maxDensity; }
    public boolean   isEmpty()      { return bins.isEmpty(); }

    /**
     * Returns local-maxima bins whose density >= minProminence * maxDensity.
     * These represent High-Volume Nodes in the price distribution.
     */
    public List<Bin> getHvnBins(double minProminence) {
        if (bins.size() < 3) return Collections.emptyList();
        List<Bin> hvns = new ArrayList<>();
        for (int i = 1; i < bins.size() - 1; i++) {
            Bin cur  = bins.get(i);
            Bin prev = bins.get(i - 1);
            Bin next = bins.get(i + 1);
            if (cur.densityNorm >= minProminence * maxDensity
                    && cur.densityNorm > prev.densityNorm
                    && cur.densityNorm > next.densityNorm) {
                hvns.add(cur);
            }
        }
        return hvns;
    }

    /**
     * Returns local-minima bins whose density < maxDensityThreshold.
     * These represent Low-Volume Nodes in the price distribution.
     */
    public List<Bin> getLvnBins(double maxDensityThreshold) {
        if (bins.size() < 3) return Collections.emptyList();
        List<Bin> lvns = new ArrayList<>();
        for (int i = 1; i < bins.size() - 1; i++) {
            Bin cur  = bins.get(i);
            Bin prev = bins.get(i - 1);
            Bin next = bins.get(i + 1);
            if (cur.densityNorm < maxDensityThreshold
                    && cur.densityNorm < prev.densityNorm
                    && cur.densityNorm < next.densityNorm) {
                lvns.add(cur);
            }
        }
        return lvns;
    }
}
