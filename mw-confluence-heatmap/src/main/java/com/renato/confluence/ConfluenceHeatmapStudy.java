// REQUIRES_SDK
package com.renato.confluence;

import com.motivewave.platform.sdk.common.DataContext;
import com.motivewave.platform.sdk.common.DataSeries;
import com.motivewave.platform.sdk.common.DrawContext;
import com.motivewave.platform.sdk.common.Instrument;
import com.motivewave.platform.sdk.common.OrderFlowBarData;
import com.motivewave.platform.sdk.study.Defaults;
import com.motivewave.platform.sdk.study.RuntimeDescriptor;
import com.motivewave.platform.sdk.study.Study;
import com.motivewave.platform.sdk.study.StudyHeader;
import com.motivewave.platform.sdk.study.settings.BooleanDescriptor;
import com.motivewave.platform.sdk.study.settings.ColorDescriptor;
import com.motivewave.platform.sdk.study.settings.DoubleDescriptor;
import com.motivewave.platform.sdk.study.settings.Group;
import com.motivewave.platform.sdk.study.settings.IntegerDescriptor;
import com.motivewave.platform.sdk.study.settings.SettingsDescriptor;
import com.motivewave.platform.sdk.study.settings.Tab;
import com.renato.confluence.detector.DetectorContext;
import com.renato.confluence.detector.LevelDetector;
import com.renato.confluence.detector.orderflow.AbsorptionDetector;
import com.renato.confluence.detector.orderflow.BarPOCDetector;
import com.renato.confluence.detector.orderflow.CVDDivergenceDetector;
import com.renato.confluence.detector.orderflow.DeltaFlipDetector;
import com.renato.confluence.detector.orderflow.HighDeltaBarDetector;
import com.renato.confluence.detector.orderflow.StackedImbalanceDetector;
import com.renato.confluence.detector.orderflow.SweepDetector;
import com.renato.confluence.detector.profile.PriorSessionLevelsDetector;
import com.renato.confluence.detector.profile.SessionVolumeProfileDetector;
import com.renato.confluence.detector.psychological.RoundNumberDetector;
import com.renato.confluence.detector.vwap.SessionVWAPDetector;
import com.renato.confluence.domain.DensityFunction;
import com.renato.confluence.domain.Level;
import com.renato.confluence.domain.LevelType;
import com.renato.confluence.engine.ConfluenceEngine;
import com.renato.confluence.render.ConfluenceSidePanelPlot;
import com.renato.confluence.render.HeatmapBandsFigure;
import com.renato.confluence.util.BarMath;
import com.renato.confluence.util.RollingStats;

import java.awt.Color;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.atomic.AtomicReference;

/**
 * ConfluenceHeatmapStudy — MotiveWave study that aggregates order-flow based
 * price levels from multiple detectors, clusters them, and renders the result
 * as a heatmap overlay and side-panel histogram.
 *
 * Installation:
 *  1. Place motivewave-sdk.jar in ~/MotiveWave/sdk/
 *  2. Run: gradle jar
 *  3. The output jar is copied to ~/MotiveWave Extensions/
 *  4. Restart MotiveWave and find "Confluence Heatmap" under Studies.
 *
 * REQUIRES_SDK: Cannot compile without motivewave-sdk.jar on classpath.
 */
@StudyHeader(
    name        = "Confluence Heatmap",
    desc        = "Order-flow confluence zones rendered as heatmap bands",
    menu        = "Renato Studies",
    overlay     = true,
    requiresBarData = true
)
public class ConfluenceHeatmapStudy extends Study {

    // ------------------------------------------------------------------ setting keys
    private static final String KEY_ENABLE_HIGH_DELTA      = "enableHighDelta";
    private static final String KEY_ENABLE_BAR_POC         = "enableBarPoc";
    private static final String KEY_ENABLE_DELTA_FLIP      = "enableDeltaFlip";
    private static final String KEY_ENABLE_ABSORPTION      = "enableAbsorption";
    private static final String KEY_ENABLE_CVD_DIV         = "enableCvdDiv";
    private static final String KEY_ENABLE_SWEEP           = "enableSweep";
    private static final String KEY_ENABLE_STACKED_IMBAL   = "enableStackedImbal";
    private static final String KEY_ENABLE_VOL_PROFILE     = "enableVolProfile";
    private static final String KEY_ENABLE_PRIOR_SESSION   = "enablePriorSession";
    private static final String KEY_ENABLE_VWAP            = "enableVwap";
    private static final String KEY_ENABLE_ROUND_NUMBERS   = "enableRoundNumbers";

    private static final String KEY_CLUSTER_TICKS          = "clusterTicks";
    private static final String KEY_CLUSTER_ATR_MULT       = "clusterAtrMult";
    private static final String KEY_EPSILON_DECAY          = "epsilonDecay";
    private static final String KEY_KDE_H_MIN              = "kdeHMin";
    private static final String KEY_MAX_LOOKBACK           = "maxLookback";

    private static final String KEY_COLOR_LOW              = "hmColorLow";
    private static final String KEY_COLOR_HIGH             = "hmColorHigh";

    // ------------------------------------------------------------------ internal state
    private final List<Level>       levelPool   = new ArrayList<>(4096);
    private final AtomicReference<DensityFunction> currentDensity
                                                = new AtomicReference<>(null);
    private volatile int activeClusterCount     = 0;

    // Detectors
    private HighDeltaBarDetector    highDeltaDetector;
    private BarPOCDetector          barPocDetector;
    private DeltaFlipDetector       deltaFlipDetector;
    private AbsorptionDetector      absorptionDetector;
    private CVDDivergenceDetector   cvdDivDetector;
    private SweepDetector           sweepDetector;
    private StackedImbalanceDetector stackedImbalDetector;
    private SessionVolumeProfileDetector volProfileDetector;
    private PriorSessionLevelsDetector   priorSessionDetector;
    private SessionVWAPDetector     vwapDetector;
    private RoundNumberDetector     roundNumberDetector;

    private List<LevelDetector>     allDetectors;

    // Shared rolling stats
    private final RollingStats deltaStats  = new RollingStats(50);
    private final RollingStats volumeStats = new RollingStats(20);

    // Render components
    private HeatmapBandsFigure     heatmapFigure;
    private ConfluenceSidePanelPlot sidePanel;

    // ------------------------------------------------------------------ Study lifecycle

    @Override
    public void initialize(Defaults defaults, RuntimeDescriptor rd) {
        defaults.setShowBars(true);

        // Build UI settings
        SettingsDescriptor sd = createSettingsDescriptor();

        Tab generalTab = sd.addTab("General");

        Group ofGroup = generalTab.addGroup("Order Flow Detectors");
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_HIGH_DELTA,    "High Delta Bars",       true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_BAR_POC,       "Bar POC",               true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_DELTA_FLIP,    "Delta Flip",            true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_ABSORPTION,    "Absorption Bars",       true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_CVD_DIV,       "CVD Divergence",        true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_SWEEP,         "Liquidity Sweeps",      true));
        ofGroup.addRow(new BooleanDescriptor(KEY_ENABLE_STACKED_IMBAL, "Stacked Imbalances",    true));

        Group profileGroup = generalTab.addGroup("Profile / VWAP");
        profileGroup.addRow(new BooleanDescriptor(KEY_ENABLE_VOL_PROFILE,   "Session Volume Profile", true));
        profileGroup.addRow(new BooleanDescriptor(KEY_ENABLE_PRIOR_SESSION, "Prior Session Levels",   true));
        profileGroup.addRow(new BooleanDescriptor(KEY_ENABLE_VWAP,          "Session VWAP + Bands",   true));
        profileGroup.addRow(new BooleanDescriptor(KEY_ENABLE_ROUND_NUMBERS, "Round Numbers",          true));

        Tab engineTab = sd.addTab("Engine");

        Group clusterGroup = engineTab.addGroup("Clustering");
        clusterGroup.addRow(new IntegerDescriptor(KEY_CLUSTER_TICKS,   "Cluster Epsilon (ticks)", 4,  1, 100, 1));
        clusterGroup.addRow(new DoubleDescriptor( KEY_CLUSTER_ATR_MULT, "Cluster ATR Multiplier",  0.15, 0.01, 2.0, 0.01));

        Group decayGroup = engineTab.addGroup("Time Decay / KDE");
        decayGroup.addRow(new DoubleDescriptor(KEY_EPSILON_DECAY, "Decay Epsilon",     0.01, 0.001, 1.0,  0.001));
        decayGroup.addRow(new DoubleDescriptor(KEY_KDE_H_MIN,     "KDE h_min ATR ×",  0.25, 0.01,  5.0,  0.01));
        decayGroup.addRow(new IntegerDescriptor(KEY_MAX_LOOKBACK,  "Max Lookback Bars", 2000, 100, 10000, 100));

        Tab displayTab = sd.addTab("Display");
        Group colorGroup = displayTab.addGroup("Heatmap Colors");
        colorGroup.addRow(new ColorDescriptor(KEY_COLOR_LOW,  "Color — Low Density",  Color.YELLOW));
        colorGroup.addRow(new ColorDescriptor(KEY_COLOR_HIGH, "Color — High Density", new Color(200, 30, 30)));

        // Register render components
        heatmapFigure = new HeatmapBandsFigure(this);
        sidePanel     = new ConfluenceSidePanelPlot(this);
        rd.declareFigure(heatmapFigure);
        rd.addPlot("confluencePanel", sidePanel);

        // Initialise detectors
        initDetectors();
    }

    @Override
    public void onSettingChanged() {
        syncDetectorEnabledFlags();
        resetAll();
    }

    @Override
    public void calculate(int index, DataContext ctx) {
        DataSeries series = ctx.getDataSeries();
        int        i      = index;

        // Update shared stats before detectors run
        double delta  = series.getAskVolume(i) - series.getBidVolume(i);
        double volume = series.getVolume(i);
        deltaStats.push(delta);
        volumeStats.push(volume);

        // Build detector context wrapping the SDK objects
        DetectorContext dctx = buildDetectorContext(series, ctx.getInstrument(), i);

        // Run all enabled detectors
        for (LevelDetector detector : allDetectors) {
            if (!detector.isEnabled()) continue;
            detector.onBarClose(dctx);
            List<Level> newLevels = detector.drainEmittedLevels();
            levelPool.addAll(newLevels);
        }

        // Prune pool size (keep last maxLookback bars' worth)
        int maxLookback = getSettings().getInt(KEY_MAX_LOOKBACK, 2000);
        prunePool(i, maxLookback);

        // Build engine settings from UI
        ConfluenceEngine.Settings engineSettings = buildEngineSettings();

        // Compute price window: ± 5 × ATR around current close
        double atr     = BarMath.atrSmoothed(
                getHighArray(series, i), getLowArray(series, i),
                getCloseArray(series, i), i, 14);
        if (atr <= 0) atr = ctx.getInstrument().getTickSize() * 50;

        double close    = series.getClose(i);
        double tickSize = ctx.getInstrument().getTickSize();
        double priceMin = close - 6.0 * atr;
        double priceMax = close + 6.0 * atr;

        // Run the confluence engine
        DensityFunction density = ConfluenceEngine.compute(
                levelPool, i,
                getHighArray(series, i), getLowArray(series, i),
                getOpenArray(series, i), getCloseArray(series, i),
                atr, tickSize, priceMin, priceMax,
                engineSettings);

        currentDensity.set(density);

        // Count active clusters (rough: count bins above 50% density threshold)
        activeClusterCount = countClusters(density);

        // Signal MotiveWave to repaint
        repaint();
    }

    // ------------------------------------------------------------------ public accessors (render layer)

    public DensityFunction getCurrentDensity() {
        return currentDensity.get();
    }

    public Color getHeatmapColorLow() {
        try {
            Color c = getSettings().getColor(KEY_COLOR_LOW);
            return c != null ? c : Color.YELLOW;
        } catch (Exception e) {
            return Color.YELLOW;
        }
    }

    public Color getHeatmapColorHigh() {
        try {
            Color c = getSettings().getColor(KEY_COLOR_HIGH);
            return c != null ? c : new Color(200, 30, 30);
        } catch (Exception e) {
            return new Color(200, 30, 30);
        }
    }

    public int getActiveClusterCount() {
        return activeClusterCount;
    }

    // ------------------------------------------------------------------ init helpers

    private void initDetectors() {
        highDeltaDetector    = new HighDeltaBarDetector(true);
        barPocDetector       = new BarPOCDetector(true);
        deltaFlipDetector    = new DeltaFlipDetector(true);
        absorptionDetector   = new AbsorptionDetector(true);
        cvdDivDetector       = new CVDDivergenceDetector(true);
        sweepDetector        = new SweepDetector(true);
        stackedImbalDetector = new StackedImbalanceDetector(true);
        volProfileDetector   = new SessionVolumeProfileDetector(true);
        priorSessionDetector = new PriorSessionLevelsDetector(true);
        vwapDetector         = new SessionVWAPDetector(true);
        roundNumberDetector  = new RoundNumberDetector(true);

        allDetectors = new ArrayList<>();
        allDetectors.add(highDeltaDetector);
        allDetectors.add(barPocDetector);
        allDetectors.add(deltaFlipDetector);
        allDetectors.add(absorptionDetector);
        allDetectors.add(cvdDivDetector);
        allDetectors.add(sweepDetector);
        allDetectors.add(stackedImbalDetector);
        allDetectors.add(volProfileDetector);
        allDetectors.add(priorSessionDetector);
        allDetectors.add(vwapDetector);
        allDetectors.add(roundNumberDetector);
    }

    private void syncDetectorEnabledFlags() {
        highDeltaDetector.setEnabled(   getSettings().getBoolean(KEY_ENABLE_HIGH_DELTA,    true));
        barPocDetector.setEnabled(      getSettings().getBoolean(KEY_ENABLE_BAR_POC,       true));
        deltaFlipDetector.setEnabled(   getSettings().getBoolean(KEY_ENABLE_DELTA_FLIP,    true));
        absorptionDetector.setEnabled(  getSettings().getBoolean(KEY_ENABLE_ABSORPTION,    true));
        cvdDivDetector.setEnabled(      getSettings().getBoolean(KEY_ENABLE_CVD_DIV,       true));
        sweepDetector.setEnabled(       getSettings().getBoolean(KEY_ENABLE_SWEEP,         true));
        stackedImbalDetector.setEnabled(getSettings().getBoolean(KEY_ENABLE_STACKED_IMBAL, true));
        volProfileDetector.setEnabled(  getSettings().getBoolean(KEY_ENABLE_VOL_PROFILE,   true));
        priorSessionDetector.setEnabled(getSettings().getBoolean(KEY_ENABLE_PRIOR_SESSION, true));
        vwapDetector.setEnabled(        getSettings().getBoolean(KEY_ENABLE_VWAP,          true));
        roundNumberDetector.setEnabled( getSettings().getBoolean(KEY_ENABLE_ROUND_NUMBERS, true));
    }

    private void resetAll() {
        levelPool.clear();
        deltaStats.reset();
        volumeStats.reset();
        currentDensity.set(null);
        activeClusterCount = 0;
        for (LevelDetector d : allDetectors) d.reset();
    }

    private ConfluenceEngine.Settings buildEngineSettings() {
        int    clusterTicks   = getSettings().getInt(KEY_CLUSTER_TICKS,    4);
        double clusterAtrMult = getSettings().getDouble(KEY_CLUSTER_ATR_MULT, 0.15);
        double epsilonDecay   = getSettings().getDouble(KEY_EPSILON_DECAY,  0.01);
        double kdeHMin        = getSettings().getDouble(KEY_KDE_H_MIN,      0.25);
        int    maxLookback    = getSettings().getInt(KEY_MAX_LOOKBACK,       2000);

        return new ConfluenceEngine.Settings(
                0,              // use per-type half-life defaults
                epsilonDecay,
                clusterTicks,
                clusterAtrMult,
                kdeHMin,
                maxLookback,
                Collections.emptyMap());
    }

    // ------------------------------------------------------------------ pool maintenance

    private void prunePool(int currentBar, int maxLookback) {
        int cutoff = currentBar - maxLookback;
        if (cutoff <= 0) return;
        levelPool.removeIf(l -> l.barIndex < cutoff);
    }

    // ------------------------------------------------------------------ cluster counting

    private int countClusters(DensityFunction density) {
        if (density == null || density.isEmpty()) return 0;
        List<DensityFunction.Bin> hvns = density.getHvnBins(0.3);
        return hvns.size();
    }

    // ------------------------------------------------------------------ array extraction helpers

    /**
     * Extracts a double[] of highs from the DataSeries for bars [0..lastIndex].
     * NOTE: For performance in production consider caching these arrays.
     */
    private static double[] getHighArray(DataSeries s, int last) {
        double[] arr = new double[last + 1];
        for (int i = 0; i <= last; i++) arr[i] = s.getHigh(i);
        return arr;
    }

    private static double[] getLowArray(DataSeries s, int last) {
        double[] arr = new double[last + 1];
        for (int i = 0; i <= last; i++) arr[i] = s.getLow(i);
        return arr;
    }

    private static double[] getOpenArray(DataSeries s, int last) {
        double[] arr = new double[last + 1];
        for (int i = 0; i <= last; i++) arr[i] = s.getOpen(i);
        return arr;
    }

    private static double[] getCloseArray(DataSeries s, int last) {
        double[] arr = new double[last + 1];
        for (int i = 0; i <= last; i++) arr[i] = s.getClose(i);
        return arr;
    }

    // ------------------------------------------------------------------ DetectorContext factory

    /**
     * Builds a DetectorContext implementation that wraps the MotiveWave SDK objects.
     * This is the only place SDK objects cross the boundary into the detector layer.
     */
    private DetectorContext buildDetectorContext(DataSeries series,
                                                 Instrument instrument,
                                                 int currentIndex) {
        return new DetectorContext() {

            @Override public int    getCurrentIndex()               { return currentIndex; }
            @Override public int    size()                          { return series.size(); }
            @Override public double getClose(int i)                 { return series.getClose(i); }
            @Override public double getHigh(int i)                  { return series.getHigh(i); }
            @Override public double getLow(int i)                   { return series.getLow(i); }
            @Override public double getOpen(int i)                  { return series.getOpen(i); }
            @Override public double getVolume(int i)                { return series.getVolume(i); }
            @Override public long   getStartTime(int i)             { return series.getStartTime(i); }

            @Override public double getBidVolume(int i) {
                try { return series.getBidVolume(i); } catch (Exception e) { return 0; }
            }
            @Override public double getAskVolume(int i) {
                try { return series.getAskVolume(i); } catch (Exception e) { return 0; }
            }
            @Override public double getDelta(int i) {
                return getAskVolume(i) - getBidVolume(i);
            }

            @Override public double getFootprintBidVolume(int barIdx, double price) {
                try {
                    OrderFlowBarData ofData = series.getOrderFlowBarData(barIdx);
                    return ofData != null ? ofData.getBidVolume(price) : 0.0;
                } catch (Exception e) { return 0.0; }
            }

            @Override public double getFootprintAskVolume(int barIdx, double price) {
                try {
                    OrderFlowBarData ofData = series.getOrderFlowBarData(barIdx);
                    return ofData != null ? ofData.getAskVolume(price) : 0.0;
                } catch (Exception e) { return 0.0; }
            }

            @Override public boolean isFootprintAvailable() {
                try {
                    OrderFlowBarData ofData = series.getOrderFlowBarData(currentIndex);
                    return ofData != null;
                } catch (Exception e) { return false; }
            }

            @Override public double getAtr14() {
                return BarMath.atrSmoothed(
                        getHighArray(series, currentIndex),
                        getLowArray(series, currentIndex),
                        getCloseArray(series, currentIndex),
                        currentIndex, 14);
            }

            @Override public double getTickSize()  { return instrument.getTickSize(); }
            @Override public String getSymbol()    { return instrument.getSymbol(); }

            @Override public RollingStats getDeltaStats()   { return deltaStats; }
            @Override public RollingStats getVolumeStats()  { return volumeStats; }

            @Override public boolean isSessionStart(int i) {
                if (i == 0) return true;
                long prevStart = series.getStartTime(i - 1);
                long curStart  = series.getStartTime(i);
                return isDifferentRthDay(prevStart, curStart);
            }

            @Override public boolean isRthSession(int i) {
                // Approximate: RTH = 09:30–16:00 ET
                long ts = series.getStartTime(i);
                Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
                cal.setTimeInMillis(ts);
                int hour = cal.get(Calendar.HOUR_OF_DAY);
                int min  = cal.get(Calendar.MINUTE);
                int totalMin = hour * 60 + min;
                return totalMin >= 570 && totalMin < 960;  // 9:30 – 16:00
            }

            @Override public void log(String level, String message) {
                // MotiveWave doesn't expose a dedicated logger in the public SDK;
                // use System.err for WARN/ERROR, suppress DEBUG/INFO.
                if ("WARN".equals(level) || "ERROR".equals(level)) {
                    System.err.println("[ConfluenceHeatmap][" + level + "] " + message);
                }
            }
        };
    }

    // ------------------------------------------------------------------ session utility

    private static boolean isDifferentRthDay(long prevMillis, long curMillis) {
        Calendar prev = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        Calendar cur  = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        prev.setTimeInMillis(prevMillis);
        cur.setTimeInMillis(curMillis);

        boolean sameDay = prev.get(Calendar.YEAR)         == cur.get(Calendar.YEAR)
                       && prev.get(Calendar.DAY_OF_YEAR)  == cur.get(Calendar.DAY_OF_YEAR);
        if (!sameDay) return true;

        // Same calendar day — check if current bar crosses RTH open (09:30 ET)
        int prevTotalMin = prev.get(Calendar.HOUR_OF_DAY) * 60 + prev.get(Calendar.MINUTE);
        int curTotalMin  = cur.get(Calendar.HOUR_OF_DAY)  * 60 + cur.get(Calendar.MINUTE);
        return prevTotalMin < 570 && curTotalMin >= 570;  // 9:30 ET = 570 min
    }
}
