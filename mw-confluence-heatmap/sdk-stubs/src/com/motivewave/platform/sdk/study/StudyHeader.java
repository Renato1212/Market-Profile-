package com.motivewave.platform.sdk.study;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface StudyHeader {
    String name()            default "";
    String desc()            default "";
    String menu()            default "";
    boolean overlay()        default false;
    boolean requiresBarData() default false;
}
