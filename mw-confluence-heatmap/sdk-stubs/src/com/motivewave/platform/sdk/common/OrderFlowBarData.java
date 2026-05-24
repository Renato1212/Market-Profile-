package com.motivewave.platform.sdk.common;

public abstract class OrderFlowBarData {
    public abstract double getBidVolume(double price);
    public abstract double getAskVolume(double price);
}
