// REQUIRES_SDK
package com.renato.confluence.render;

import com.motivewave.platform.sdk.common.DrawContext;
import com.motivewave.platform.sdk.draw.Figure;
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
 * Chart overlay that renders the confluence density as horizontal heatmap bands.
 *
 * Rendering pipeline:
 *  1. Iterate over density bins where densityNorm >= minDisplayThreshold.
 *  2. Convert each bin's price to a Y pixel via DrawContext.getYForPrice().
 *  3. Merge adjacent bins with |Δdensity| < MERGE_TOLERANCE into continuous bands.
 *  4. Fill each band with a colour interpolated from lowColor → highColor by density.
 *  5. Apply AlphaComposite for transparency.
 *  6. Draw a distinct POC line with a price label.
 *
 * REQUIRES_SDK: This file imports MotiveWave SDK classes and cannot compile
 * without motivewave-sdk.jar on the classpath.
 */
public class HeatmapBandsFigure extends Figure {

    private static final double MIN_DISPLAY_THRESHOLD = 0.05;
    private static final double MERGE_TOLERANCE       = 0.05;
    private static final float  MAX_OPACITY           = 0.75f;
    private static final int    POC_LINE_THICKNESS    = 2;

    private final ConfluenceHeatmapStudy study;

    public HeatmapBandsFigure(ConfluenceHeatmapStudy study) {
        this.study = study;
    }

    @Override
    public void draw(Graphics2D g, DrawContext ctx) {
        DensityFunction density = study.getCurrentDensity();
        if (density == null || density.isEmpty()) return;

        List<DensityFunction.Bin> bins = density.getBins();
        if (bins.isEmpty()) return;

        Rectangle bounds = ctx.getPlotBounds();
        int chartLeft    = bounds.x;
        int chartRight   = bounds.x + bounds.width;

        Color colorLow  = study.getHeatmapColorLow();
        Color colorHigh = study.getHeatmapColorHigh();

        Composite originalComposite = g.getComposite();
        Font      originalFont      = g.getFont();
        Color     originalColor     = g.getColor();

        try {
            drawBands(g, ctx, bins, chartLeft, chartRight,
                    colorLow, colorHigh);
            drawPocLine(g, ctx, density, chartLeft, chartRight);
        } finally {
            g.setComposite(originalComposite);
            g.setFont(originalFont);
            g.setColor(originalColor);
        }
    }

    // ------------------------------------------------------------------ band drawing

    private void drawBands(Graphics2D g, DrawContext ctx,
                           List<DensityFunction.Bin> bins,
                           int xLeft, int xRight,
                           Color colorLow, Color colorHigh) {

        int n = bins.size();
        if (n == 0) return;

        // Estimate bin height from price step and first two bins
        double tickSize = (n > 1)
                ? Math.abs(bins.get(1).price - bins.get(0).price)
                : 0.01;

        int i = 0;
        while (i < n) {
            DensityFunction.Bin bin = bins.get(i);
            if (bin.densityNorm < MIN_DISPLAY_THRESHOLD) {
                i++;
                continue;
            }

            // Merge adjacent similar-density bins into one band
            double groupDensity = bin.densityNorm;
            int    groupStart   = i;
            int    groupEnd     = i;

            while (groupEnd + 1 < n) {
                DensityFunction.Bin next = bins.get(groupEnd + 1);
                if (next.densityNorm >= MIN_DISPLAY_THRESHOLD
                        && Math.abs(next.densityNorm - groupDensity) <= MERGE_TOLERANCE) {
                    groupDensity = (groupDensity + next.densityNorm) / 2.0;
                    groupEnd++;
                } else {
                    break;
                }
            }

            // Y coordinates for the band (price decreases going down on most charts)
            double topPrice    = bins.get(groupEnd).price + tickSize / 2.0;
            double bottomPrice = bins.get(groupStart).price - tickSize / 2.0;
            int    yTop        = ctx.getYForPrice(topPrice);
            int    yBottom     = ctx.getYForPrice(bottomPrice);

            if (yTop > yBottom) {
                int tmp = yTop; yTop = yBottom; yBottom = tmp;
            }
            int bandHeight = Math.max(1, yBottom - yTop);

            // Colour and opacity
            float   opacity = (float) (groupDensity * MAX_OPACITY);
            Color   color   = interpolateColor(colorLow, colorHigh, groupDensity);

            g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, opacity));
            g.setColor(color);
            g.fillRect(xLeft, yTop, xRight - xLeft, bandHeight);

            i = groupEnd + 1;
        }
    }

    // ------------------------------------------------------------------ POC line

    private void drawPocLine(Graphics2D g, DrawContext ctx,
                             DensityFunction density,
                             int xLeft, int xRight) {
        double pocPrice = density.getPocPrice();
        if (Double.isNaN(pocPrice)) return;

        int yPoc = ctx.getYForPrice(pocPrice);

        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, 0.90f));
        g.setColor(new Color(255, 50, 50));

        // Draw thick horizontal POC line
        for (int t = 0; t < POC_LINE_THICKNESS; t++) {
            g.drawLine(xLeft, yPoc + t, xRight, yPoc + t);
        }

        // Label
        g.setFont(new Font("SansSerif", Font.BOLD, 10));
        String label = String.format("POC %.2f", pocPrice);
        FontMetrics fm = g.getFontMetrics();
        int labelX = xRight - fm.stringWidth(label) - 4;
        int labelY = yPoc - 3;
        g.setColor(Color.WHITE);
        g.fillRect(labelX - 1, labelY - fm.getAscent(),
                fm.stringWidth(label) + 2, fm.getHeight());
        g.setColor(new Color(180, 30, 30));
        g.drawString(label, labelX, labelY);
    }

    // ------------------------------------------------------------------ colour utility

    private static Color interpolateColor(Color low, Color high, double t) {
        t = Math.max(0.0, Math.min(1.0, t));
        int r = (int) (low.getRed()   + t * (high.getRed()   - low.getRed()));
        int gv = (int) (low.getGreen() + t * (high.getGreen() - low.getGreen()));
        int b = (int) (low.getBlue()  + t * (high.getBlue()  - low.getBlue()));
        return new Color(
                Math.max(0, Math.min(255, r)),
                Math.max(0, Math.min(255, gv)),
                Math.max(0, Math.min(255, b)));
    }
}
