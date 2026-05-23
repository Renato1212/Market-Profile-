# MotiveWave SDK Reconnaissance Notes

## Compilation Environment

The MotiveWave SDK jar is **not** included in this repository. Place it at:

```
~/MotiveWave/sdk/motivewave-sdk.jar
```

Files marked `// REQUIRES_SDK` will not compile without it. The engine, domain, detector logic, and util layers are pure Java and compile/run with JUnit 5 only.

---

## Footprint / Order Flow API

### Per-bar bid/ask volume at a specific price tick

```java
import com.motivewave.platform.sdk.common.OrderFlowBarData;

DataSeries series = ctx.getDataSeries();
OrderFlowBarData ofData = series.getOrderFlowBarData(barIndex);
if (ofData != null) {
    double bidVol = ofData.getBidVolume(price);  // bid volume at that tick
    double askVol = ofData.getAskVolume(price);  // ask volume at that tick
}
```

Only available in **Order Flow Edition**. Always null-check `ofData` before use. If `null`, footprint data is unavailable for that bar (fall back to bar-level bid/ask totals).

### Bar-level totals

```java
double bid = series.getBidVolume(barIndex);
double ask = series.getAskVolume(barIndex);
double delta = ask - bid;
```

---

## Session VWAP and Band Access

Compute manually inside the study — MW does not expose a pre-built VWAP. Use running sums:

```java
double cumulativePV = 0;   // Σ(price × volume)
double cumulativeVol = 0;  // Σ(volume)
double cumulatePVV = 0;    // Σ(volume × price²) for variance

// On each bar:
double typicalPrice = (high + low + close) / 3.0;
cumulativePV  += typicalPrice * volume;
cumulativeVol += volume;
double vwap   = cumulativePV / cumulativeVol;
double variance = (cumulatePVV / cumulativeVol) - (vwap * vwap);
double stdDev  = Math.sqrt(Math.max(variance, 0));
```

Reset accumulators when `isSessionStart(index)` returns true.

---

## Study Lifecycle

### `onLoad(StudyHeader header)`

Called once when the study loads on a chart. Use this for one-time initialization (e.g., building internal data structures). In MotiveWave, the full historical bar series is available here, but `calculate()` is the intended place for bar processing.

### `calculate(int index, DataContext ctx)`

Called for **each bar** during historical replay and for each tick/bar on live data. `index` is the bar index being calculated (0 = oldest, `series.size()-1` = newest). This is the main computation entry point.

### `onSettingChanged()`

Called when the user modifies a setting in the study properties panel. Re-read settings and trigger a full recalculation.

---

## Settings UI Pattern

```java
@Override
public void initialize(Defaults defaults, RuntimeDescriptor rd) {
    // Create a settings tab
    SettingsDescriptor sd = createSettingsDescriptor();
    Tab tab = sd.addTab("General");

    // Add a group within the tab
    Group grp = tab.addGroup("Order Flow Detectors");
    grp.addRow(new BooleanDescriptor("enableHighDelta", "High Delta Bars", true));
    grp.addRow(new IntegerDescriptor("clusterTicks", "Cluster Epsilon (ticks)", 4, 1, 100, 1));
    grp.addRow(new DoubleDescriptor("epsilonDecay", "Decay Epsilon", 0.01, 0.001, 1.0, 0.001));
    grp.addRow(new ColorDescriptor("hmColorLow", "Heatmap Color Low", Color.YELLOW));
    grp.addRow(new ColorDescriptor("hmColorHigh", "Heatmap Color High", Color.RED));
}
```

### Reading settings in `calculate()`

```java
boolean enabled = getSettings().getBoolean("enableHighDelta");
int ticks       = getSettings().getInt("clusterTicks");
double epsilon  = getSettings().getDouble("epsilonDecay");
Color colorLow  = getSettings().getColor("hmColorLow");
```

---

## Right-Axis Side Panel Plot

Extend `com.motivewave.platform.sdk.study.Plot`:

```java
public class ConfluenceSidePanelPlot extends Plot {
    @Override
    public void draw(Graphics2D g, DrawContext ctx) {
        Rectangle bounds = ctx.getPlotBounds();
        // bounds.x, bounds.y, bounds.width, bounds.height define the panel area
        DataSeries series = ctx.getDataSeries();
        // ctx.getYForPrice(price) — maps price to Y pixel in this plot
        // ctx.getPriceForY(y)     — inverse
    }
}
```

Register in `initialize()`:
```java
rd.addPlot("confluencePanel", new ConfluenceSidePanelPlot(this));
```

---

## Overlay Chart Figure

Extend `com.motivewave.platform.sdk.draw.Figure`:

```java
public class HeatmapBandsFigure extends Figure {
    @Override
    public void draw(Graphics2D g, DrawContext ctx) {
        Rectangle bounds = ctx.getPlotBounds();
        // Iterate density bins, map price to Y, draw horizontal bands
    }
}
```

Register in `initialize()`:
```java
rd.declareFigure(new HeatmapBandsFigure(this));
```

Both a `Figure` (chart overlay) and one or more `Plot` instances (side panel) can coexist in the same study.

---

## Alpha Compositing (Opacity)

Standard Java2D `AlphaComposite` works on the `Graphics2D` passed to `draw()`:

```java
Composite original = g.getComposite();
g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 0.6f));
g.fillRect(x, y, width, height);
g.setComposite(original);  // Always restore
```

---

## Color Gradient Interpolation

```java
private Color interpolateColor(Color low, Color high, double t) {
    // t in [0, 1]
    int r = (int) (low.getRed()   + t * (high.getRed()   - low.getRed()));
    int g = (int) (low.getGreen() + t * (high.getGreen() - low.getGreen()));
    int b = (int) (low.getBlue()  + t * (high.getBlue()  - low.getBlue()));
    return new Color(r, g, b);
}
```

---

## StackedImbalanceDetector Notes

Fully implemented using the footprint API above. Imbalance ratio threshold: ask/bid >= 3.0 (or bid/ask >= 3.0 for sell side). Stack = 3+ consecutive imbalances in same direction. Only activated when `isFootprintAvailable()` returns true; otherwise silently skips with a single WARN log per session.

---

## Key SDK Import Packages (for reference)

```
com.motivewave.platform.sdk.study.Study
com.motivewave.platform.sdk.study.StudyHeader
com.motivewave.platform.sdk.study.RuntimeDescriptor
com.motivewave.platform.sdk.study.Defaults
com.motivewave.platform.sdk.common.DataContext
com.motivewave.platform.sdk.common.DataSeries
com.motivewave.platform.sdk.common.Instrument
com.motivewave.platform.sdk.common.OrderFlowBarData
com.motivewave.platform.sdk.common.DrawContext
com.motivewave.platform.sdk.draw.Figure
com.motivewave.platform.sdk.study.Plot
com.motivewave.platform.sdk.study.settings.SettingsDescriptor
com.motivewave.platform.sdk.study.settings.Tab
com.motivewave.platform.sdk.study.settings.Group
com.motivewave.platform.sdk.study.settings.BooleanDescriptor
com.motivewave.platform.sdk.study.settings.IntegerDescriptor
com.motivewave.platform.sdk.study.settings.DoubleDescriptor
com.motivewave.platform.sdk.study.settings.ColorDescriptor
```
