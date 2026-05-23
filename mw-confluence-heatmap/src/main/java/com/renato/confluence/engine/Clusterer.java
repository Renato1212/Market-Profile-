package com.renato.confluence.engine;

import com.renato.confluence.domain.Cluster;
import com.renato.confluence.domain.Level;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * Greedy single-pass price-space clustering.
 *
 * Algorithm:
 * 1. Sort levels by mid-price.
 * 2. Start a new cluster with the first level.
 * 3. For each subsequent level, compute the current cluster's weighted centroid.
 *    If the level's mid-price is within {@code epsilon} of the centroid, absorb it;
 *    otherwise close the cluster and start a new one.
 *
 * This is O(n log n) and produces stable, deterministic results.
 *
 * Pure Java — no SDK imports.
 */
public final class Clusterer {

    /**
     * Merge {@code levels} into clusters whose constituent mid-prices are all
     * within {@code epsilon} of the running weighted centroid.
     *
     * @param levels  levels to cluster (not modified)
     * @param epsilon maximum distance from cluster centroid to admit a new level
     * @return list of clusters, sorted by centroid price ascending
     */
    public static List<Cluster> greedyMerge(List<Level> levels, double epsilon) {
        if (levels.isEmpty()) return Collections.emptyList();

        // Sort by mid price
        List<Level> sorted = new ArrayList<>(levels);
        sorted.sort(Comparator.comparingDouble(Level::midPrice));

        List<Cluster> clusters = new ArrayList<>();
        List<Level>   current  = new ArrayList<>();
        current.add(sorted.get(0));

        for (int i = 1; i < sorted.size(); i++) {
            Level  next     = sorted.get(i);
            double centroid = weightedCentroid(current);
            if (Math.abs(next.midPrice() - centroid) <= epsilon) {
                current.add(next);
            } else {
                clusters.add(buildCluster(current));
                current = new ArrayList<>();
                current.add(next);
            }
        }
        clusters.add(buildCluster(current));
        return clusters;
    }

    // ------------------------------------------------------------------ private

    private static double weightedCentroid(List<Level> levels) {
        double weightedSum = 0.0;
        double totalWeight = 0.0;
        for (Level l : levels) {
            weightedSum += l.midPrice() * l.rawStrength;
            totalWeight += l.rawStrength;
        }
        if (totalWeight <= 0.0) {
            // Fall back to simple average
            double sum = 0.0;
            for (Level l : levels) sum += l.midPrice();
            return sum / levels.size();
        }
        return weightedSum / totalWeight;
    }

    private static Cluster buildCluster(List<Level> levels) {
        double centroid     = weightedCentroid(levels);
        double totalStrength = 0.0;
        double priceLow     = Double.MAX_VALUE;
        double priceHigh    = -Double.MAX_VALUE;

        for (Level l : levels) {
            totalStrength += l.rawStrength;
            if (l.priceLow  < priceLow)  priceLow  = l.priceLow;
            if (l.priceHigh > priceHigh) priceHigh = l.priceHigh;
        }

        // For point levels, low == high == centroid
        if (priceLow == Double.MAX_VALUE) {
            priceLow  = centroid;
            priceHigh = centroid;
        }

        return new Cluster(centroid, priceLow, priceHigh, totalStrength, levels);
    }

    private Clusterer() {}
}
