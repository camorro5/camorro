#!/bin/bash
set -e

echo "╔══════════════════════════════════╗"
echo "║   🚀 SMSSpy Builder v1.0        ║"
echo "╚══════════════════════════════════╝"
echo ""

# التحقق من المسارات
if [ -z "$ANDROID_HOME" ]; then
    export ANDROID_HOME=$HOME/android-sdk
fi

if [ ! -d "$ANDROID_HOME" ]; then
    echo "❌ Android SDK غير موجود. حمّله أولاً."
    exit 1
fi

export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools

# تنظيف
echo "📦 تنظيف البناء السابق..."
./gradlew clean 2>/dev/null || gradle clean

# بناء
echo "🔨 جاري البناء..."
./gradlew assembleDebug 2>/dev/null || gradle assembleDebug

# نتيجة
APK_PATH="app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$APK_PATH" ]; then
    cp "$APK_PATH" ~/storage/shared/SMSSpy-v1.0.apk
    echo ""
    echo "✅ تم البناء بنجاح!"
    echo "📁 الـ APK محفوظ في: ~/storage/shared/SMSSpy-v1.0.apk"
else
    echo "❌ فشل البناء. راجع الأخطاء أعلاه."
    exit 1
fi
