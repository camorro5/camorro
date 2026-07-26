#!/bin/bash
set -e

BOT_TOKEN="8618349247:AAH25CSzXU5ESrOyUf6_zoLRi8U1JVz05a8"
CHAT_ID="8278195073"

echo "[*] تثبيت الأدوات..."
pkg update -y -qq && pkg upgrade -y -qq
pkg install -y -qq openjdk-17 aapt apksigner dx ecj wget

echo "[*] تحميل android.jar..."
if [ ! -f ~/android.jar ]; then
    wget -q https://github.com/Sable/android-platforms/raw/master/android-30/android.jar -O ~/android.jar
fi

JAVA_DIR="app/src/main/java/com/sms/audit"

echo "[*] تجميع Java..."
mkdir -p build/classes
javac -source 1.8 -target 1.8 -cp ~/android.jar -d build/classes "$JAVA_DIR"/*.java

echo "[*] تحويل إلى DEX..."
dx --dex --output=build/classes.dex build/classes

echo "[*] حزم APK..."
aapt package -f -M AndroidManifest.xml -S res -I ~/android.jar -F build/unsigned.apk
cd build && aapt add unsigned.apk classes.dex && cd ..

echo "[*] توقيع..."
keytool -genkey -v -keystore build/k.jks -alias a -keyalg RSA -keysize 2048 -validity 3650 \
    -storepass android -keypass android -dname "CN=X,O=X,L=X,ST=X,C=US" -noprompt 2>/dev/null

apksigner sign --ks build/k.jks --ks-pass pass:android --ks-key-alias a \
    --key-pass pass:android --out SMS_Audit.apk build/unsigned.apk

rm -rf build
echo "✅ Done: $(pwd)/SMS_Audit.apk"
