package com.renato.confluence.engine;

import com.renato.confluence.domain.Cluster;
import com.renato.confluence.domain.DensityFunction;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class KernelDensityEstimatorTest {

    // ------------------------------------------------------------------ helpers

    private static Cluster makeCluster(double centroid, double strength) {
        Level l = new Level(centroid, centroid, strength, LevelType.HIGH_DELTA_BAR, 0L, 0,
                Collections.emptyMap());
        return new Cluster(centroid, centroid, centroid, strength, List.of(l));
    }

    private static Cluster makeClusterZone(double low, double high, double strength) {
        double centroid = (low + high) / 2.0;
        Level l = new Level(low, high, strength, LevelType.HIGH_DELTA_BAR, 0L, 0,
                Collections.emptyMap());
        return new Cluster(centroid, low, high, strength, List.of(l));
    }

    // ------------------------------------------------------------------ empty inputs

    @Test
    void emptyClusters_returnsEmptyDensity() {
        DensityFunction density = KernelDensityEstimator.compute(
                Collections.emptyList(),
                95.0, 105.0, 0.25, 2.0, 0.25);
        assertTrue(density.isEmpty());
    }

    @Test
    void invalidTickSize_returnsEmpty() {
        Cluster c = makeCluster(100.0, 1.0);
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 95.0, 105.0, 0.0, 2.0, 0.25);
        assertTrue(density.isEmpty());
    }

    @Test
    void invertedRange_returnsEmpty() {
        Cluster c = makeCluster(100.0, 1.0);
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 105.0, 95.0, 0.25, 2.0, 0.25);
        assertTrue(density.isEmpty());
    }

    // ------------------------------------------------------------------ single cluster

    @Test
    void singleCluster_peakAtCentroid() {
        Cluster c = makeCluster(100.0, 1.0);
        double tickSize = 0.25;

        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 98.0, 102.0, tickSize, 2.0, 0.25);

        assertFalse(density.isEmpty());

        // The POC should be at or very close to 100.0
        assertEquals(100.0, density.getPocPrice(), tickSize,
                "POC price should be at the cluster centroid (within 1 tick)");
    }

    @Test
    void singleCluster_maxDensityIsOne() {
        Cluster c = makeCluster(100.0, 1.0);
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 98.0, 102.0, 0.25, 2.0, 0.25);

        assertEquals(1.0, density.getMaxDensity(), 1e-9,
                "Normalised density maximum must be 1.0");
    }

    @Test
    void singleCluster_fallsOffAwayFromCentroid() {
        Cluster c = makeCluster(100.0, 2.0);
        double tickSize = 0.25;
        // bandwidth = max(clusterWidth=0, hMin=0.25*2=0.5) = 0.5
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 98.0, 102.0, tickSize, 2.0, 0.25);

        // Find density at 100.0 and at 100.5
        double densityAt100  = getDensityAt(density, 100.0, tickSize);
        double densityAt1005 = getDensityAt(density, 100.5, tickSize);

        // 100.0 should have higher density than 100.5
        assertTrue(densityAt100 > densityAt1005,
                "Density should decrease away from centroid");
    }

    // ------------------------------------------------------------------ two clusters

    @Test
    void twoClusters_twoPeaks() {
        Cluster c1 = makeCluster(99.0, 1.0);
        Cluster c2 = makeCluster(101.0, 1.0);
        double tickSize = 0.25;

        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c1, c2), 97.0, 103.0, tickSize, 1.0, 0.25);

        // There should be two peaks — one near 99 and one near 101
        List<DensityFunction.Bin> hvns = density.getHvnBins(0.3);
        assertTrue(hvns.size() >= 2, "Expected at least two HVN peaks for two separate clusters");

        // Max normalised density must still be 1.0
        assertEquals(1.0, density.getMaxDensity(), 1e-9);
    }

    @Test
    void strongerCluster_hasPoc() {
        // Cluster at 100.0 with strength 1.0, cluster at 102.0 with strength 5.0
        Cluster c1 = makeCluster(100.0, 1.0);
        Cluster c2 = makeCluster(102.0, 5.0);
        double tickSize = 0.25;

        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c1, c2), 98.0, 104.0, tickSize, 0.5, 0.25);

        // POC should be near 102.0 (stronger cluster)
        assertEquals(102.0, density.getPocPrice(), 0.5,
                "POC should be at the stronger cluster");
    }

    // ------------------------------------------------------------------ normalisation

    @Test
    void allBinsNormalisedBetweenZeroAndOne() {
        Cluster c1 = makeCluster(100.0, 3.0);
        Cluster c2 = makeCluster(101.0, 1.5);
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c1, c2), 98.0, 103.0, 0.25, 1.0, 0.25);

        for (DensityFunction.Bin bin : density.getBins()) {
            assertTrue(bin.densityNorm >= 0.0 && bin.densityNorm <= 1.0,
                    "Bin density " + bin.densityNorm + " is out of [0,1] range");
        }
    }

    // ------------------------------------------------------------------ bin count

    @Test
    void binCountMatchesPriceRange() {
        Cluster c = makeCluster(100.0, 1.0);
        double priceMin = 100.0;
        double priceMax = 102.0;
        double tickSize = 0.5;

        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), priceMin, priceMax, tickSize, 1.0, 0.25);

        // Expected bins: ceil((102-100)/0.5) + 1 = 5 bins
        int expectedBins = (int) Math.ceil((priceMax - priceMin) / tickSize) + 1;
        assertEquals(expectedBins, density.getBins().size());
    }

    // ------------------------------------------------------------------ HVN / LVN

    @Test
    void singleCluster_onePeakHvn() {
        Cluster c = makeCluster(100.0, 1.0);
        DensityFunction density = KernelDensityEstimator.compute(
                List.of(c), 98.0, 102.0, 0.25, 1.0, 0.25);

        // The POC bin should be identifiable as an HVN
        List<DensityFunction.Bin> hvns = density.getHvnBins(0.5);
        assertFalse(hvns.isEmpty(), "Single cluster should produce at least one HVN");
    }

    // ------------------------------------------------------------------ helper

    private static double getDensityAt(DensityFunction density, double targetPrice,
                                       double tickSize) {
        double closest = 0;
        double minDist = Double.MAX_VALUE;
        for (DensityFunction.Bin bin : density.getBins()) {
            double dist = Math.abs(bin.price - targetPrice);
            if (dist < minDist) {
                minDist = dist;
                closest = bin.densityNorm;
            }
        }
        return closest;
    }
}
