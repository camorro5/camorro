# إبقاء الكلاسات الأساسية
-keep class com.spyapp.** { *; }

# منع حذف BuildConfig
-keep class com.spyapp.BuildConfig { *; }

# إزالة Logs من Release
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
    public static *** w(...);
}

# تجنب كشف اسم البوت
-keepattributes Signature
-keepattributes *Annotation*
