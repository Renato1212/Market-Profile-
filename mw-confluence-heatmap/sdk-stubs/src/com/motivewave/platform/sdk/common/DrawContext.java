package com.motivewave.platform.sdk.common;

import java.awt.Rectangle;

public abstract class DrawContext {
    public abstract Rectangle getPlotBounds();
    public abstract int       getYForPrice(double price);
    public abstract double    getPriceForY(int y);
    public abstract DataSeries getDataSeries();
}
