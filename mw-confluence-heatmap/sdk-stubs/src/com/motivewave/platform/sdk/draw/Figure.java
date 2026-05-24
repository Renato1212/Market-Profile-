package com.motivewave.platform.sdk.draw;

import com.motivewave.platform.sdk.common.DrawContext;
import java.awt.Graphics2D;

public abstract class Figure {
    public abstract void draw(Graphics2D g, DrawContext ctx);
}
