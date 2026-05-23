package com.renato.confluence.engine;

import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelStatus;
import com.renato.confluence.domain.LevelType;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class TimeDecayTest {

    private static Level makeLevel(double rawStrength, LevelType type, int barIndex) {
        return new Level(100.0, 100.0, rawStrength, type, 0L, barIndex,
                Collections.emptyMap());
    }

    // ------------------------------------------------------------------ basic decay

    @Test
    void decayHalfLifeEquals100Age100() {
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        // HIGH_DELTA_BAR defaultHalfLife = 100
        List<Level> result = TimeDecay.apply(List.of(level), 100);

        assertEquals(1, result.size());
        double expected = Math.exp(-1.0);  // exp(-age/halfLife) = exp(-100/100)
        assertEquals(expected, result.get(0).rawStrength, 1e-9);
    }

    @Test
    void decayHalfLifeEquals100Age200() {
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        List<Level> result = TimeDecay.apply(List.of(level), 200);

        assertEquals(1, result.size());
        double expected = Math.exp(-2.0);  // exp(-200/100)
        assertEquals(expected, result.get(0).rawStrength, 1e-9);
    }

    @Test
    void decayWithZeroHalfLifeOverride_usesPerTypeDefault() {
        // halfLifeOverride = 0 means use per-type default (100 for HIGH_DELTA_BAR)
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        List<Level> withOverride = TimeDecay.apply(List.of(level), 100,
                Collections.emptyMap(), 0.001);
        List<Level> withoutOverride = TimeDecay.apply(List.of(level), 100);

        assertEquals(1, withOverride.size());
        assertEquals(1, withoutOverride.size());
        assertEquals(withOverride.get(0).rawStrength, withoutOverride.get(0).rawStrength, 1e-12);
    }

    // ------------------------------------------------------------------ epsilon cutoff

    @Test
    void levelDecayedBelowEpsilonIsDropped() {
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        // age = 10000 bars with halfLife=100 → tiny decayed strength
        List<Level> result = TimeDecay.apply(List.of(level), 10000,
                Collections.emptyMap(), 0.01);
        assertTrue(result.isEmpty(), "Fully decayed level should be dropped");
    }

    @Test
    void levelJustAboveEpsilonSurvives() {
        // Choose an age such that exp(-age/halfLife) is just above epsilon=0.01
        // halfLife=100, age=400 → exp(-4) ≈ 0.0183 > 0.01
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        List<Level> result = TimeDecay.apply(List.of(level), 400,
                Collections.emptyMap(), 0.01);
        assertEquals(1, result.size());
        assertTrue(result.get(0).rawStrength >= 0.01);
    }

    // ------------------------------------------------------------------ VWAP no-decay

    @Test
    void vwapTypesNeverDecay() {
        Level vwap = makeLevel(1.0, LevelType.SESSION_VWAP, 0);
        // Huge age — should not decay because SESSION_VWAP has MAX_VALUE halfLife
        List<Level> result = TimeDecay.apply(List.of(vwap), 1_000_000);

        assertEquals(1, result.size());
        assertEquals(1.0, result.get(0).rawStrength, 1e-12);
    }

    @Test
    void roundNumberTypesNeverDecay() {
        Level rn = makeLevel(0.5, LevelType.ROUND_NUMBER_MAJOR, 0);
        List<Level> result = TimeDecay.apply(List.of(rn), 999_999);

        assertEquals(1, result.size());
        assertEquals(0.5, result.get(0).rawStrength, 1e-12);
    }

    // ------------------------------------------------------------------ override map

    @Test
    void halfLifeOverrideRespected() {
        Level level = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        Map<String, Integer> overrides = new HashMap<>();
        overrides.put("HIGH_DELTA_BAR", 50);  // override to 50 bars

        // age=50, halfLife=50 → exp(-1) ≈ 0.368
        List<Level> result = TimeDecay.apply(List.of(level), 50, overrides, 0.001);

        assertEquals(1, result.size());
        assertEquals(Math.exp(-1.0), result.get(0).rawStrength, 1e-9);
    }

    // ------------------------------------------------------------------ multiple levels

    @Test
    void emptyInputReturnsEmpty() {
        List<Level> result = TimeDecay.apply(Collections.emptyList(), 100);
        assertTrue(result.isEmpty());
    }

    @Test
    void multipleLevelsDecayIndependently() {
        Level l1 = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);   // halfLife=100, age=100
        Level l2 = makeLevel(2.0, LevelType.HVN, 0);              // halfLife=300, age=100

        List<Level> result = TimeDecay.apply(Arrays.asList(l1, l2), 100);

        assertEquals(2, result.size());
        double expectedL1 = Math.exp(-100.0 / 100);
        double expectedL2 = 2.0 * Math.exp(-100.0 / 300);
        assertEquals(expectedL1, result.get(0).rawStrength, 1e-9);
        assertEquals(expectedL2, result.get(1).rawStrength, 1e-9);
    }

    // ------------------------------------------------------------------ immutability

    @Test
    void originalLevelNotMutated() {
        Level original = makeLevel(1.0, LevelType.HIGH_DELTA_BAR, 0);
        TimeDecay.apply(List.of(original), 100);
        assertEquals(1.0, original.rawStrength, "Original level must not be mutated");
    }
}
