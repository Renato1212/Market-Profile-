package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class NormalizerTest {

    private static Level makeLevel(double rawStrength, LevelType type) {
        return new Level(100.0, 100.0, rawStrength, type, 0L, 0,
                Collections.emptyMap());
    }

    // ------------------------------------------------------------------ same type

    @Test
    void twoLevelsSameType_normalised() {
        Level l1 = makeLevel(0.5, LevelType.HIGH_DELTA_BAR);
        Level l2 = makeLevel(1.0, LevelType.HIGH_DELTA_BAR);

        List<Level> result = Normalizer.maxScaleWithinDetector(Arrays.asList(l1, l2));

        assertEquals(2, result.size());
        // Max = 1.0, so l1 → 0.5, l2 → 1.0
        assertEquals(0.5, result.get(0).rawStrength, 1e-12);
        assertEquals(1.0, result.get(1).rawStrength, 1e-12);
    }

    @Test
    void singleLevel_normalisedToOne() {
        Level l = makeLevel(42.0, LevelType.BAR_POC);
        List<Level> result = Normalizer.maxScaleWithinDetector(List.of(l));

        assertEquals(1, result.size());
        assertEquals(1.0, result.get(0).rawStrength, 1e-12);
    }

    // ------------------------------------------------------------------ different types

    @Test
    void twoDifferentTypes_scaledIndependently() {
        Level ofLevel  = makeLevel(3.0, LevelType.HIGH_DELTA_BAR);  // max for OF type = 3.0
        Level hvnLevel = makeLevel(6.0, LevelType.HVN);             // max for HVN type = 6.0

        List<Level> result = Normalizer.maxScaleWithinDetector(Arrays.asList(ofLevel, hvnLevel));

        assertEquals(2, result.size());
        // Both should normalise to 1.0 since each is the max of its type
        assertEquals(1.0, result.get(0).rawStrength, 1e-12);
        assertEquals(1.0, result.get(1).rawStrength, 1e-12);
    }

    @Test
    void mixedTypes_perTypeCeiling() {
        // OF: max=10.0, so 5.0→0.5 and 10.0→1.0
        // HVN: max=2.0, so 2.0→1.0 and 1.0→0.5
        Level of1  = makeLevel(5.0,  LevelType.HIGH_DELTA_BAR);
        Level of2  = makeLevel(10.0, LevelType.HIGH_DELTA_BAR);
        Level hvn1 = makeLevel(2.0,  LevelType.HVN);
        Level hvn2 = makeLevel(1.0,  LevelType.HVN);

        List<Level> result = Normalizer.maxScaleWithinDetector(
                Arrays.asList(of1, of2, hvn1, hvn2));

        assertEquals(4, result.size());
        assertEquals(0.5, result.get(0).rawStrength, 1e-12); // of1
        assertEquals(1.0, result.get(1).rawStrength, 1e-12); // of2
        assertEquals(1.0, result.get(2).rawStrength, 1e-12); // hvn1
        assertEquals(0.5, result.get(3).rawStrength, 1e-12); // hvn2
    }

    // ------------------------------------------------------------------ edge cases

    @Test
    void maxZero_allDropToZero() {
        Level l1 = makeLevel(0.0, LevelType.HIGH_DELTA_BAR);
        Level l2 = makeLevel(0.0, LevelType.HIGH_DELTA_BAR);

        List<Level> result = Normalizer.maxScaleWithinDetector(Arrays.asList(l1, l2));

        assertEquals(2, result.size());
        assertEquals(0.0, result.get(0).rawStrength, 1e-12);
        assertEquals(0.0, result.get(1).rawStrength, 1e-12);
    }

    @Test
    void emptyInput_returnsEmpty() {
        List<Level> result = Normalizer.maxScaleWithinDetector(Collections.emptyList());
        assertTrue(result.isEmpty());
    }

    // ------------------------------------------------------------------ immutability

    @Test
    void originalLevelsNotMutated() {
        Level l1 = makeLevel(0.5, LevelType.HIGH_DELTA_BAR);
        Level l2 = makeLevel(1.0, LevelType.HIGH_DELTA_BAR);
        Normalizer.maxScaleWithinDetector(Arrays.asList(l1, l2));

        assertEquals(0.5, l1.rawStrength, "Original must not be mutated");
        assertEquals(1.0, l2.rawStrength, "Original must not be mutated");
    }
}
