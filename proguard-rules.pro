# إخفاء الكلاسات الحساسة
-keep class com.smsgrabber.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class com.google.gson.** { *; }

# إزالة معلومات التصحيح
-renamesourcefileattribute SourceFile
-keepattributes SourceFile,LineNumberTable
