package com.motivewave.platform.sdk.common;

public abstract class DataSeries {
    public abstract int    size();
    public abstract double getClose(int index);
    public abstract double getHigh(int index);
    public abstract double getLow(int index);
    public abstract double getOpen(int index);
    public abstract double getVolume(int index);
    public abstract long   getStartTime(int index);
    public abstract double getBidVolume(int index);
    public abstract double getAskVolume(int index);
    public abstract OrderFlowBarData getOrderFlowBarData(int index);
}
