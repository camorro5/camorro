# إخفاء الكلاس
-keep class com.invisible.** { *; }
-dontwarn com.invisible.**

# منع تتبع التطبيق
-renamesourcefileattribute SourceFile
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable
