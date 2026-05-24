package com.motivewave.platform.sdk.study;

import com.motivewave.platform.sdk.common.DataContext;
import com.motivewave.platform.sdk.study.settings.SettingsDescriptor;
import java.awt.Color;

public abstract class Study {

    public static class Settings {
        public boolean getBoolean(String key, boolean defaultVal) { return defaultVal; }
        public boolean getBoolean(String key)                     { return true; }
        public int     getInt(String key, int defaultVal)         { return defaultVal; }
        public int     getInt(String key)                         { return 0; }
        public double  getDouble(String key, double defaultVal)   { return defaultVal; }
        public double  getDouble(String key)                      { return 0.0; }
        public Color   getColor(String key)                       { return null; }
        public Color   getColor(String key, Color defaultVal)     { return defaultVal; }
    }

    protected Settings             getSettings()             { return new Settings(); }
    protected SettingsDescriptor   createSettingsDescriptor() { return new SettingsDescriptor(); }
    protected void                 repaint()                  {}

    public abstract void initialize(Defaults defaults, RuntimeDescriptor rd);
    public abstract void calculate(int index, DataContext ctx);
    public void onSettingChanged() {}
}
