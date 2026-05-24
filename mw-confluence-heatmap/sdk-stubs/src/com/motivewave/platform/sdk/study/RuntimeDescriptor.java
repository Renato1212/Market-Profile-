package com.motivewave.platform.sdk.study;

import com.motivewave.platform.sdk.draw.Figure;

public class RuntimeDescriptor {
    public void declareFigure(Figure figure)       {}
    public void addPlot(String id, Plot plot)      {}
    public void exportValue(Object descriptor)     {}
    public void setLabelSettings(String... keys)   {}
}
