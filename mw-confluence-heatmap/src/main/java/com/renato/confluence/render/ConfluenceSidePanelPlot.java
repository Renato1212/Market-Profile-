// REQUIRES_SDK
package com.renato.confluence.render;

import com.motivewave.platform.sdk.common.DrawContext;
import com.motivewave.platform.sdk.study.Plot;
import com.renato.confluence.ConfluenceHeatmapStudy;
import com.renato.confluence.domain.DensityFunction;

import java.awt.AlphaComposite;
import java.awt.Color;
import java.awt.Composite;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.util.List;

/**
 * Right-axis side panel showing the confluence density as a horizontal histogram.
 *
 * Each price bin is rendered as a horizontal bar extending from the right edge
 * of the panel, with length proportional to its normalised density.  Colour
 * follows the same gradient as the heatmap overlay.
 *
 * Annotations:
 *  - POC price label
 *  - Top 3 HVN price labels
 *  - Footer: active cluster count
 *
 * REQUIRES_SDK: This file imports MotiveWave SDK classes and cannot compile
 * without motivewave-sdk.jar on the classpath.
 */
public class ConfluenceSidePanelPlot extends Plot {

    private static final double MIN_DISPLAY_THRESHOLD = 0.03;
    private static final double HVN_PROMINENCE        = 0.5;
    private static final float  MAX_OPACITY           = 0.80f;
    private static final int    TOP_HVN_COUNT         = 3;

    private final ConfluenceHeatmapStudy study;

    public ConfluenceSidePanelPlot(ConfluenceHeatmapStudy study) {
        this.study = study;
    }

    @Override
    public void draw(Graphics2D g, DrawContext ctx) {
        DensityFunction density = study.getCurrentDensity();
        if (density == null || density.isEmpty()) return;

        Rectangle bounds = ctx.getPlotBounds();
        if (bounds.width <= 0 || bounds.height <= 0) return;

        List<DensityFunction.Bin> bins  = density.getBins();
        List<DensityFunction.Bin> hvns  = density.getHvnBins(HVN_PROMINENCE);
        double                    poc   = density.getPocPrice();
        int                       clusterCount = study.getActiveClusterCount();

        Color colorLow  = study.getHeatmapColorLow();
        Color colorHigh = study.getHeatmapColorHigh();

        Composite originalComposite = g.getComposite();
        Color     originalColor     = g.getColor();
        Font      originalFont      = g.getFont();

        try {
            drawHistogram(g, ctx, bins, bounds, colorLow, colorHigh);
            drawPocLabel(g, ctx, poc, bounds);
            drawHvnLabels(g, ctx, hvns, bounds);
            drawFooter(g, bounds, clusterCount);
        } finally {
            g.setComposite(originalComposite);
            g.setColor(originalColor);
            g.setFont(originalFont);
        }
    }

    // ------------------------------------------------------------------ histogram bars

    private void drawHistogram(Graphics2D g, DrawContext ctx,
                               List<DensityFunction.Bin> bins,
                               Rectangle bounds,
                               Color colorLow, Color colorHigh) {
        int panelRight = bounds.x + bounds.width;
        int maxBarWidth = bounds.width - 2;  // leave 2px margin on left

        int n = bins.size();
        double tickSize = (n > 1)
                ? Math.abs(bins.get(1).price - bins.get(0).price)
                : 0.01;

        for (DensityFunction.Bin bin : bins) {
            if (bin.densityNorm < MIN_DISPLAY_THRESHOLD) continue;

            int yCenter = ctx.getYForPrice(bin.price);
            int barHeight = Math.max(1,
                    (int) Math.abs(ctx.getYForPrice(bin.price - tickSize / 2.0)
                                   - ctx.getYForPrice(bin.price + tickSize / 2.0)));
            int barWidth  = (int) (bin.densityNorm * maxBarWidth);
            int xLeft     = panelRight - barWidth;
            int yTop      = yCenter - barHeight / 2;

            float  opacity = (float) (bin.densityNorm * MAX_OPACITY);
            Color  color   = interpolateColor(colorLow, colorHigh, bin.densityNorm);

            g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, opacity));
            g.setColor(color);
            g.fillRect(xLeft, yTop, barWidth, barHeight);
        }
    }

    // ------------------------------------------------------------------ labels

    private void drawPocLabel(Graphics2D g, DrawContext ctx,
                              double pocPrice, Rectangle bounds) {
        if (Double.isNaN(pocPrice)) return;

        int yPoc = ctx.getYForPrice(pocPrice);
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 1.0f));
        g.setColor(new Color(220, 40, 40));
        g.drawLine(bounds.x, yPoc, bounds.x + bounds.width, yPoc);

        g.setFont(new Font("SansSerif", Font.BOLD, 9));
        String label = String.format("POC %.2f", pocPrice);
        g.drawString(label, bounds.x + 2, yPoc - 2);
    }

    private void drawHvnLabels(Graphics2D g, DrawContext ctx,
                               List<DensityFunction.Bin> hvns,
                               Rectangle bounds) {
        if (hvns.isEmpty()) return;
        g.setFont(new Font("SansSerif", Font.PLAIN, 8));
        g.setColor(new Color(200, 200, 60));
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 0.9f));

        int count = Math.min(TOP_HVN_COUNT, hvns.size());
        // Pick top N by density
        List<DensityFunction.Bin> sorted = new java.util.ArrayList<>(hvns);
        sorted.sort((a, b) -> Double.compare(b.densityNorm, a.densityNorm));

        for (int k = 0; k < count; k++) {
            DensityFunction.Bin hvn = sorted.get(k);
            int y = ctx.getYForPrice(hvn.price);
            String label = String.format("H %.2f", hvn.price);
            g.drawString(label, bounds.x + 2, y - 1);
        }
    }

    private void drawFooter(Graphics2D g, Rectangle bounds, int clusterCount) {
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 0.85f));
        g.setColor(Color.LIGHT_GRAY);
        g.setFont(new Font("SansSerif", Font.PLAIN, 9));

        String footer = String.format("Clusters: %d", clusterCount);
        FontMetrics fm = g.getFontMetrics();
        int x = bounds.x + (bounds.width - fm.stringWidth(footer)) / 2;
        int y = bounds.y + bounds.height - 4;
        g.drawString(footer, x, y);
    }

    // ------------------------------------------------------------------ colour utility

    private static Color interpolateColor(Color low, Color high, double t) {
        t = Math.max(0.0, Math.min(1.0, t));
        int r  = (int) (low.getRed()   + t * (high.getRed()   - low.getRed()));
        int gv = (int) (low.getGreen() + t * (high.getGreen() - low.getGreen()));
        int b  = (int) (low.getBlue()  + t * (high.getBlue()  - low.getBlue()));
        return new Color(
                Math.max(0, Math.min(255, r)),
                Math.max(0, Math.min(255, gv)),
                Math.max(0, Math.min(255, b)));
    }
}
