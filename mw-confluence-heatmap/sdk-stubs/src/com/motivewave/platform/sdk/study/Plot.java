package com.motivewave.platform.sdk.study;

import com.motivewave.platform.sdk.common.DrawContext;
import java.awt.Graphics2D;

public abstract class Plot {
    public abstract void draw(Graphics2D g, DrawContext ctx);
}
