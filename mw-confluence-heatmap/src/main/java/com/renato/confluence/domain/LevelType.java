package com.renato.confluence.domain;

public enum LevelType {

    // ---- Order flow ----
    HIGH_DELTA_BAR          (Category.ORDERFLOW,    100,           50),
    BAR_POC                 (Category.ORDERFLOW,    100,           50),
    DELTA_FLIP              (Category.ORDERFLOW,    100,           40),
    ABSORPTION              (Category.ORDERFLOW,    150,           75),
    CVD_DIVERGENCE_BULL     (Category.ORDERFLOW,    150,           65),
    CVD_DIVERGENCE_BEAR     (Category.ORDERFLOW,    150,           65),
    SWEEP_HIGH              (Category.ORDERFLOW,    150,           70),
    SWEEP_LOW               (Category.ORDERFLOW,    150,           70),
    STACKED_IMBALANCE_BUY   (Category.ORDERFLOW,    200,           80),
    STACKED_IMBALANCE_SELL  (Category.ORDERFLOW,    200,           80),

    // ---- Volume profile ----
    HVN                     (Category.PROFILE,      300,           70),
    LVN                     (Category.PROFILE,      300,           50),
    DEVELOPING_POC          (Category.PROFILE,       50,           80),
    NAKED_POC               (Category.PROFILE,     1500,           90),

    // ---- Session levels ----
    PRIOR_DAY_HIGH          (Category.SESSION,      1500,          85),
    PRIOR_DAY_LOW           (Category.SESSION,      1500,          85),
    PRIOR_DAY_CLOSE         (Category.SESSION,      1500,          85),
    SETTLEMENT              (Category.SESSION,      1500,          85),

    // ---- VWAP ----
    SESSION_VWAP            (Category.VWAP,         Integer.MAX_VALUE, 80),
    VWAP_SIGMA_POS_1        (Category.VWAP,         Integer.MAX_VALUE, 60),
    VWAP_SIGMA_NEG_1        (Category.VWAP,         Integer.MAX_VALUE, 60),
    VWAP_SIGMA_POS_2        (Category.VWAP,         Integer.MAX_VALUE, 40),
    VWAP_SIGMA_NEG_2        (Category.VWAP,         Integer.MAX_VALUE, 40),

    // ---- Psychological ----
    ROUND_NUMBER_MAJOR      (Category.PSYCHOLOGICAL, Integer.MAX_VALUE, 60),
    ROUND_NUMBER_MEDIUM     (Category.PSYCHOLOGICAL, Integer.MAX_VALUE, 50),
    ROUND_NUMBER_MINOR      (Category.PSYCHOLOGICAL, Integer.MAX_VALUE, 40),
    ROUND_NUMBER_SUBMINOR   (Category.PSYCHOLOGICAL, Integer.MAX_VALUE, 25);

    // ------------------------------------------------------------------
    public enum Category {
        ORDERFLOW, PROFILE, SESSION, VWAP, STRUCTURAL, PSYCHOLOGICAL
    }

    public final Category category;
    public final int      defaultHalfLifeBars;
    public final int      defaultWeight;          // 0-100 percentage basis

    LevelType(Category category, int defaultHalfLifeBars, int defaultWeight) {
        this.category            = category;
        this.defaultHalfLifeBars = defaultHalfLifeBars;
        this.defaultWeight       = defaultWeight;
    }
}
