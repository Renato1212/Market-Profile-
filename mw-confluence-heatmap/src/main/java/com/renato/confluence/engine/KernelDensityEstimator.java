package com.renato.confluence.engine;

import com.renato.confluence.domain.Cluster;
import com.renato.confluence.domain.DensityFunction;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Epanechnikov-like kernel density estimator over a uniform price grid.
 *
 * For each cluster, a triangular kernel (bilinear falloff) is spread across
 * neighbouring bins within the adaptive bandwidth.  The bandwidth is:
 *
 *   h = max(cluster.width(), hMinAtrMultiplier * atr)
 *
 * This ensures thin/point clusters still produce a meaningful spread.
 * All output density values are normalised so the maximum bin = 1.0.
 *
 * Pure Java — no SDK imports.
 */
public final class KernelDensityEstimator {

    /**
     * Compute the density function over a uniform price grid.
     *
     * @param clusters           clusters to spread into the density grid
     * @param priceMin           lowest grid price (inclusive)
     * @param priceMax           highest grid price (inclusive)
     * @param tickSize           distance between adjacent grid bins
     * @param atr                current ATR (used for minimum bandwidth)
     * @param hMinAtrMultiplier  minimum bandwidth = this * atr
     * @return normalised density function; empty if clusters or tickSize invalid
     */
    public static DensityFunction compute(List<Cluster> clusters,
                                          double priceMin, double priceMax,
                                          double tickSize, double atr,
                                          double hMinAtrMultiplier) {
        if (clusters.isEmpty() || tickSize <= 0 || priceMax <= priceMin) {
            return new DensityFunction(Collections.emptyList());
        }

        int numBins = (int) Math.ceil((priceMax - priceMin) / tickSize) + 1;
        if (numBins <= 0) return new DensityFunction(Collections.emptyList());

        double[] density = new double[numBins];
        double hMin = Math.max(hMinAtrMultiplier * atr, tickSize);

        for (Cluster cluster : clusters) {
            double bandwidth = Math.max(cluster.width(), hMin);
            if (bandwidth <= 0) bandwidth = hMin;
            double center = cluster.centroid;

            // Only iterate bins within the kernel's support
            int startBin = Math.max(0,
                    (int) Math.floor((center - bandwidth - priceMin) / tickSize));
            int endBin   = Math.min(numBins - 1,
                    (int) Math.ceil((center + bandwidth - priceMin) / tickSize));

            for (int b = startBin; b <= endBin; b++) {
                double price  = priceMin + b * tickSize;
                double u      = Math.abs(price - center) / bandwidth;   // u in [0, 1]
                // Triangular (tent) kernel: k(u) = max(0, 1 - u)
                double k      = Math.max(0.0, 1.0 - u);
                density[b]   += cluster.strength * k;
            }
        }

        // Find the maximum for normalisation
        double maxDensity = 0.0;
        for (double d : density) {
            if (d > maxDensity) maxDensity = d;
        }

        // Build normalised bin list
        List<DensityFunction.Bin> bins = new ArrayList<>(numBins);
        for (int b = 0; b < numBins; b++) {
            double price      = priceMin + b * tickSize;
            double normalised = maxDensity > 0.0 ? density[b] / maxDensity : 0.0;
            bins.add(new DensityFunction.Bin(price, normalised));
        }

        return new DensityFunction(bins);
    }

    private KernelDensityEstimator() {}
}
