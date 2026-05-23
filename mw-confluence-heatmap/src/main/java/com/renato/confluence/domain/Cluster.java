package com.renato.confluence.domain;

import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Immutable result of spatial clustering of {@link Level} instances.
 */
public final class Cluster {

    public final double        centroid;          // strength-weighted price centroid
    public final double        priceLow;
    public final double        priceHigh;
    public final double        strength;          // sum of constituent strengths
    public final List<Level>   constituents;
    public final Set<LevelType> constituentTypes;

    public Cluster(double centroid, double priceLow, double priceHigh,
                   double strength, List<Level> constituents) {
        this.centroid   = centroid;
        this.priceLow   = priceLow;
        this.priceHigh  = priceHigh;
        this.strength   = strength;
        this.constituents = Collections.unmodifiableList(List.copyOf(constituents));
        this.constituentTypes = constituents.stream()
                .map(l -> l.type)
                .collect(Collectors.toUnmodifiableSet());
    }

    public double width() { return priceHigh - priceLow; }

    @Override
    public String toString() {
        return String.format("Cluster{centroid=%.4f, strength=%.4f, size=%d}",
                centroid, strength, constituents.size());
    }
}
