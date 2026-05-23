package com.renato.confluence.engine;

import com.renato.confluence.domain.Cluster;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ClustererTest {

    private static Level makeLevel(double price, double strength) {
        return new Level(price, price, strength, LevelType.HIGH_DELTA_BAR, 0L, 0,
                Collections.emptyMap());
    }

    private static Level makeLevelZone(double low, double high, double strength) {
        return new Level(low, high, strength, LevelType.HIGH_DELTA_BAR, 0L, 0,
                Collections.emptyMap());
    }

    // ------------------------------------------------------------------ basic splits

    @Test
    void threePoints_twoSplitClusters() {
        // 100 and 100.5 within epsilon=1.0 of each other; 105 is outside
        Level l1 = makeLevel(100.0, 1.0);
        Level l2 = makeLevel(100.5, 1.0);
        Level l3 = makeLevel(105.0, 1.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2, l3), 1.0);

        assertEquals(2, clusters.size(), "Expected two clusters");

        // Cluster 1 should contain l1 and l2
        Cluster c1 = clusters.get(0);
        Cluster c2 = clusters.get(1);

        // Sort by centroid (ascending, since we sorted by midPrice)
        assertTrue(c1.centroid < c2.centroid);
        assertEquals(2, c1.constituents.size());
        assertEquals(1, c2.constituents.size());
        assertEquals(105.0, c2.centroid, 1e-9);
    }

    @Test
    void allWithinEpsilon_singleCluster() {
        Level l1 = makeLevel(10.0, 1.0);
        Level l2 = makeLevel(10.5, 1.0);
        Level l3 = makeLevel(11.0, 1.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2, l3), 2.0);

        assertEquals(1, clusters.size());
        assertEquals(3, clusters.get(0).constituents.size());
    }

    @Test
    void allBeyondEpsilon_separateClusters() {
        Level l1 = makeLevel(100.0, 1.0);
        Level l2 = makeLevel(110.0, 1.0);
        Level l3 = makeLevel(120.0, 1.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2, l3), 5.0);

        assertEquals(3, clusters.size());
    }

    // ------------------------------------------------------------------ centroid weighting

    @Test
    void centroidIsStrengthWeighted_notSimpleAverage() {
        // l1 at 100 with strength 1.0, l2 at 110 with strength 9.0
        // Weighted centroid = (100 * 1 + 110 * 9) / (1 + 9) = 109.0
        // Simple average = 105.0
        Level l1 = makeLevel(100.0, 1.0);
        Level l2 = makeLevel(110.0, 9.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2), 15.0);

        assertEquals(1, clusters.size());
        assertEquals(109.0, clusters.get(0).centroid, 1e-9);
        assertNotEquals(105.0, clusters.get(0).centroid, "Should be weighted, not simple average");
    }

    @Test
    void totalStrengthIsSumOfConstituents() {
        Level l1 = makeLevel(100.0, 2.0);
        Level l2 = makeLevel(101.0, 3.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2), 5.0);

        assertEquals(1, clusters.size());
        assertEquals(5.0, clusters.get(0).strength, 1e-9);
    }

    // ------------------------------------------------------------------ cluster bounds

    @Test
    void clusterBoundsSpanAllConstituents() {
        Level l1 = makeLevelZone(99.0, 100.0, 1.0);  // [99, 100]
        Level l2 = makeLevelZone(100.5, 101.5, 1.0); // [100.5, 101.5]

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2), 5.0);

        assertEquals(1, clusters.size());
        assertEquals(99.0,  clusters.get(0).priceLow,  1e-9);
        assertEquals(101.5, clusters.get(0).priceHigh, 1e-9);
    }

    // ------------------------------------------------------------------ edge cases

    @Test
    void emptyInput_returnsEmpty() {
        List<Cluster> clusters = Clusterer.greedyMerge(Collections.emptyList(), 1.0);
        assertTrue(clusters.isEmpty());
    }

    @Test
    void singleLevel_oneCluster() {
        Level l = makeLevel(50.0, 1.0);
        List<Cluster> clusters = Clusterer.greedyMerge(List.of(l), 1.0);

        assertEquals(1, clusters.size());
        assertEquals(50.0, clusters.get(0).centroid, 1e-9);
        assertEquals(1, clusters.get(0).constituents.size());
    }

    @Test
    void sortOrderDoesNotAffectResult() {
        // Input in reverse price order
        Level l1 = makeLevel(105.0, 1.0);
        Level l2 = makeLevel(100.0, 1.0);
        Level l3 = makeLevel(100.5, 1.0);

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2, l3), 1.0);

        assertEquals(2, clusters.size());
        // {100, 100.5} and {105}
        assertTrue(clusters.get(0).centroid < clusters.get(1).centroid);
        assertEquals(2, clusters.get(0).constituents.size());
        assertEquals(1, clusters.get(1).constituents.size());
    }

    @Test
    void zeroEpsilon_eachLevelItsOwnCluster() {
        Level l1 = makeLevel(100.0, 1.0);
        Level l2 = makeLevel(100.0001, 1.0);  // Very close but > 0 distance

        List<Cluster> clusters = Clusterer.greedyMerge(Arrays.asList(l1, l2), 0.0);

        assertEquals(2, clusters.size());
    }
}
